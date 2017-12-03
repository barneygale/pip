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

client_spec_template = """
Owner:  {user}
Host:   {host}
Client: {name}
Root:   {client_root}
View:   {server_root} //{name}/...
"""


class Perforce(VersionControl):
    name = 'p4'
    dirname = '.p4ignore'  # Not actually a directory.
    repo_name = 'workspace'
    schemes = (
        'p4+p4',
        'p4+tcp',
        'p4+tcp4',
        'p4+tcp6',
        'p4+tcp46',
        'p4+tcp64',
        'p4+ssl',
        'p4+ssl4',
        'p4+ssl6',
        'p4+ssl46',
        'p4+ssl64')

    @classmethod
    def prepare_client(cls, client_root, server_root):
        name = "pip_" + "".join(
            random.choice(string.digits + string.ascii_lowercase)
            for _ in range(32))
        user = getpass.getuser()
        host = socket.gethostname()

        # Write client spec
        spec_path = os.path.join(client_root, ".p4spec")
        with open(spec_path, "w") as fd:
            fd.write(
                client_spec_template.format(
                    user=user,
                    host=host,
                    name=name,
                    client_root=client_root,
                    server_root=server_root))

        # Write .p4ignore
        with open(os.path.join(client_root, ".p4ignore"), "w") as fd:
            fd.write("\n".join((".p4spec", ".p4ignore")))

        # Build environment
        environ = {
            'P4CLIENT': name,
            'P4EDITOR': "%s '%s'" % (
                "move" if sys.platform.startswith("win") else "mv",
                spec_path),
            'P4IGNORE': '.p4ignore'
        }

        return name, environ

    def get_port_path_rev(self):
        url, rev = self.get_url_rev()
        url_parts = url.split("//", 3)

        # Build P4PORT
        port = ""
        if url_parts[0] != "p4:":
            port += url_parts[0]
        if len(url_parts) > 2:
            port += url_parts[1]
        if port == "":
            port = os.environ.get("P4PORT", "")

        # Build path
        path = "//%s/..." % url_parts[-1]
        if rev:
            path += "@%s" % rev

        return port, path, rev

    def obtain(self, dest):
        port, depot_path, rev = self.get_port_path_rev()
        rev_options = self.make_rev_options(rev)
        if self.check_destination(dest, None, rev_options):

            # Create directory
            if not os.path.exists(dest):
                os.mkdir(dest)

            client_name, client_environ = self.prepare_client(dest, depot_path)
            client_environ['P4PORT'] = port
            command_args = dict(
                cwd=dest,
                extra_environ=client_environ,
                show_stdout=False)

            # Sync
            logger.info('Syncing "%s"', depot_path)
            self.run_command(cmd=['client'], **command_args)
            self.run_command(cmd=['sync'], **command_args)
            self.run_command(cmd=['client', '-d', client_name], **command_args)

    def is_commit_id_equal(self, dest, name):
        raise NotImplementedError

    def get_src_requirement(self, dist, location):
        raise NotImplementedError

    def update(self, dest, rev_options):
        raise NotImplementedError

    def switch(self, dest, url, rev_options):
        raise NotImplementedError

    def get_base_rev_args(self, rev):
        raise NotImplementedError

    def get_url(self, location):
        raise NotImplementedError

    def get_revision(self, location):
        raise NotImplementedError

    def export(self, location):
        raise NotImplementedError


vcs.register(Perforce)
