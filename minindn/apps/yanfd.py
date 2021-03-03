# -*- Mode:python; c-file-style:"gnu"; indent-tabs-mode:nil -*- */
#
# Copyright (C) 2015-2019, The University of Memphis,
#                          Arizona Board of Regents,
#                          Regents of the University of California.
# Copyright (C) 2021, Eric Newberry.
#
# This file is part of Mini-NDN.
# See AUTHORS.md for a complete list of Mini-NDN authors and contributors.
#
# Mini-NDN is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mini-NDN is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mini-NDN, e.g., in COPYING.md file.
# If not, see <http://www.gnu.org/licenses/>.

from minindn.apps.application import Application
from minindn.util import copyExistentFile
from minindn.minindn import Minindn

import toml

class YaNfd(Application):

    def __init__(self, node, fwThreads=8, logLevel='INFO', csSize=65536, csPolicy='lru'):
        Application.__init__(self, node)

        self.logLevel = node.params['params'].get('nfd-log-level', logLevel)

        self.confFile = '{}/yanfd.toml'.format(self.homeDir)
        self.logFile = 'yanfd.log'
        self.sockFile = '/run/{}.sock'.format(node.name)
        self.ndnFolder = '{}/.ndn'.format(self.homeDir)
        self.clientConf = '{}/client.conf'.format(self.ndnFolder)

        # Copy yanfd.toml file from /usr/local/etc/ndn or /etc/ndn to the node's home directory
        # Use yanfd.toml as default configuration for YaNFD, else use the sample
        possibleConfPaths = ['/usr/local/etc/ndn/yanfd.toml', '/etc/ndn/yanfd.toml']
        copyExistentFile(node, possibleConfPaths, self.confFile)

        # Load TOML config
        config = toml.load(self.confFile)

        # Set number of forwarding threads
        config["fw"]["threads"] = fwThreads

        # Set log level
        config["core"]["log_level"] = self.logLevel
        # Open the conf file and change socket file name
        config["faces"]["unix"]["socket_path"] = self.sockFile

        # Set CS parameters
        config["tables"]["content_store"]["capacity"] = csSize
        config["tables"]["content_store"]["replacement_policy"] = csPolicy
        #node.cmd('infoedit -f {} -s tables.cs_unsolicited_policy -v {}'.format(self.confFile, csUnsolicitedPolicy))

        # Save TOML config
        configOut = open(self.confFile, 'w')
        toml.dump(config, configOut)
        configOut.close()

        # Make NDN folder
        node.cmd('mkdir -p {}'.format(self.ndnFolder))

        # Copy client configuration to host
        possibleClientConfPaths = ['/usr/local/etc/ndn/client.conf.sample', '/etc/ndn/client.conf.sample']
        copyExistentFile(node, possibleClientConfPaths, self.clientConf)

        # Change the unix socket
        node.cmd('sudo sed -i "s|;transport|transport|g" {}'.format(self.clientConf))
        node.cmd('sudo sed -i "s|nfd.sock|{}.sock|g" {}'.format(node.name, self.clientConf))

        if not Minindn.ndnSecurityDisabled:
            # Generate key and install cert for /localhost/operator to be used by NFD
            node.cmd('ndnsec-keygen /localhost/operator | ndnsec-install-cert -')

    def start(self):
        Application.start(self, 'yanfd --config {}'.format(self.confFile), logfile=self.logFile)
        Minindn.sleep(2)
