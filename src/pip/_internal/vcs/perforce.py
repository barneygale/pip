from __future__ import absolute_import

import getpass
import logging
import os
import random
import socket
import string
import sys

from pip._internal.vcs import VersionControl, vcs

logger = logging.getLogger(__name__)

client_user = getpass.getuser()
client_host = socket.gethostname()
client_spec_template = """
Owner:  {client_user}
Host:   {client_host}
Client: {client_name}
Root:   {client_root}
View:   {server_root} //{client_name}/...
"""


class Perforce(VersionControl):
    name = 'p4'
    repo_name = 'workspace'
    schemes = ('p4+p4',)

    def get_url_rev(self):
        url, rev = super(Perforce, self).get_url_rev()

        # Add recursive token to URL
        if not url.endswith("/..."):
            url = url.rstrip("/") + "/..."

        return url, rev

    def obtain(self, dest):
        url, rev = self.get_url_rev()
        rev_options = self.make_rev_options(rev)
        if self.check_destination(dest, url, rev_options):

            # Create directory
            if not os.path.exists(dest):
                os.mkdir(dest)

            # Set up client and server roots
            client_root = dest
            server_root = url.split("p4:")[1]
            if rev_options.rev:
                server_root += "@%s" % rev_options.rev

            # Set up client
            client_name = self.make_client_name()
            client_spec_path = os.path.join(dest, "p4-client-spec.txt")

            # Create temporary client specification
            with open(client_spec_path, "w") as fd:
                fd.write(self.make_client_spec(
                    client_name,
                    client_root,
                    server_root))

            # Set up command-runner arguments
            command_args = dict(
                cwd=dest,
                extra_environ=self.make_client_environ(
                    client_name,
                    client_spec_path),
                show_stdout=False)

            # Sync
            logger.info('Syncing "%s"', server_root)
            self.run_command(cmd=['client'], **command_args)
            self.run_command(cmd=['sync'], **command_args)
            self.run_command(cmd=['client', '-d', client_name], **command_args)

    @classmethod
    def make_client_name(cls):
        length = 32
        charset = string.digits + string.ascii_lowercase
        return "pip_" + "".join(random.choice(charset) for _ in range(length))

    @classmethod
    def make_client_spec(cls, client_name, client_root, server_root):
        return client_spec_template.format(
                client_user=client_user,
                client_host=client_host,
                client_name=client_name,
                client_root=client_root,
                server_root=server_root)

    @classmethod
    def make_client_environ(cls, client_name, client_spec_path):
        cmd = "move" if sys.platform.startswith("win") else "mv"
        return {
            'P4CLIENT': client_name,
            'P4EDITOR': "%s '%s'" % (cmd, client_spec_path)}

    @classmethod
    def controls_location(cls, location):
        # No straightforward way to determine this, so always return False.
        return False

    def is_commit_id_equal(self, dest, name):
        # Never called due to controls_location() returning False
        raise NotImplementedError

    def get_src_requirement(self, dist, location):
        # Never called due to controls_location() returning False
        raise NotImplementedError

    def update(self, dest, rev_options):
        # Never called due to controls_location() returning False
        raise NotImplementedError

    def switch(self, dest, url, rev_options):
        # Never called due to controls_location() returning False
        raise NotImplementedError

    def get_base_rev_args(self, rev):
        # Never called because we don't implement switch()
        raise NotImplementedError

    def get_url(self, location):
        # Never called because we don't call get_info()
        raise NotImplementedError

    def get_revision(self, location):
        # Never called because we don't call get_info()
        raise NotImplementedError

    def export(self, location):
        # Not possible with perforce
        raise NotImplementedError


vcs.register(Perforce)
