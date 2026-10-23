"""Exercise the real installer in isolated home/XDG directories."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class StartupInstallationTests(unittest.TestCase):
    def setUp(self):
        probe = subprocess.run(['/usr/bin/python3', '-c',
            'import gi, requests; gi.require_version("Gtk", "3.0"); '
            'gi.require_version("AyatanaAppIndicator3", "0.1"); '
            'from gi.repository import Gtk, AyatanaAppIndicator3'], capture_output=True)
        if probe.returncode:
            self.skipTest('GTK/Ayatana bindings required; use installed system or GI_TYPELIB_PATH')
        self.temp = tempfile.TemporaryDirectory(prefix='speedcheck-install-')
        self.addCleanup(self.temp.cleanup)
        # Exercise spaces and characters with special meanings in unit files.
        self.home = Path(self.temp.name) / 'home space%$'
        self.home.mkdir()
        (self.home / 'runtime').mkdir(mode=0o700)
        self.config = self.home / 'config'
        self.data = self.home / 'data'
        self.state = self.home / 'state'
        self.units = self.config / 'systemd/user'
        self.env = dict(os.environ, HOME=str(self.home), XDG_CONFIG_HOME=str(self.config),
                        XDG_DATA_HOME=str(self.data), XDG_STATE_HOME=str(self.state),
                        DBUS_SESSION_BUS_ADDRESS='', DISPLAY='', WAYLAND_DISPLAY='',
                        XDG_RUNTIME_DIR=str(self.home / 'runtime'), GSETTINGS_BACKEND='memory')
        self.autostart = self.config / 'autostart/speedcheck-linux.desktop'
        self.service = self.units / 'speedcheck-linux-headless.service'
        self.link = self.units / 'gnome-shell-headless.service.wants' / self.service.name

    def run_script(self, name, *args):
        result = subprocess.run([str(REPO / name), *args], env=self.env,
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_regular_desktop_keeps_xdg_startup_without_headless_dependency(self):
        self.run_script('install.sh')
        self.assertTrue(self.autostart.is_file())
        self.assertFalse(self.service.exists())
        self.assertFalse(self.link.is_symlink())
        prefs = self.config / 'speedcheck-linux/config.json'
        prefs.parent.mkdir(parents=True)
        prefs.write_text(json.dumps({'launch_on_login': False}))
        self.run_script('install.sh')
        self.assertFalse(self.autostart.exists())
        self.run_script('uninstall.sh')
        self.assertTrue(prefs.exists())

    def test_headless_startup_respects_toggle_and_uninstall_scope(self):
        self.units.mkdir(parents=True)
        shell = self.units / 'gnome-shell-headless.service'
        shell.write_text('[Service]\nExecStart=/bin/true\n')
        sentinel = self.units / 'unrelated.txt'
        sentinel.write_text('keep')
        state = self.state / 'speedcheck-linux/state.json'
        state.parent.mkdir(parents=True)
        state.write_text('{"cached": true}')
        self.run_script('install.sh')
        self.assertEqual(self.link.resolve(), self.service)
        self.assertTrue(self.autostart.exists())
        text = self.service.read_text()
        self.assertIn('BindsTo=gnome-shell-headless.service', text)
        self.assertIn('Restart=on-failure', text)
        self.assertIn('home space%%$', text)
        if shutil.which('systemd-analyze'):
            env = dict(self.env, SYSTEMD_UNIT_PATH=str(self.units) + ':/usr/lib/systemd/user:/lib/systemd/user')
            result = subprocess.run(['systemd-analyze', '--user', 'verify', str(self.service)],
                                    env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
        prefs = self.config / 'speedcheck-linux/config.json'
        prefs.parent.mkdir(parents=True)
        prefs.write_text(json.dumps({'launch_on_login': False}))
        self.run_script('install.sh')
        self.assertFalse(self.autostart.exists())
        self.assertTrue(self.link.is_symlink())  # Unit condition gates startup.
        self.assertEqual(json.loads(state.read_text()), {'cached': True})
        self.run_script('uninstall.sh')
        self.assertFalse(self.service.exists())
        self.assertFalse(self.link.is_symlink())
        self.assertTrue(shell.exists())
        self.assertEqual(sentinel.read_text(), 'keep')
        self.assertTrue(state.exists())
        self.run_script('uninstall.sh', '--purge')
        self.assertFalse(state.exists())
        self.assertTrue(shell.exists())
