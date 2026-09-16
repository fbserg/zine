"""Check portable cost lookup and deployment without production credentials."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repo = self.base / 'custom-checkout'
        (self.repo / 'scripts').mkdir(parents=True)
        self.env = {'PATH': os.environ['PATH'], 'HOME': str(self.base / 'home')}

    def run_deploy(self):
        shutil.copy(ROOT / 'scripts/deploy.sh', self.repo / 'scripts/deploy.sh')
        return subprocess.run(['bash', str(self.repo / 'scripts/deploy.sh')],
                              env=self.env, capture_output=True, text=True)

    def test_production_entry_points_reject_unsafe_names_before_writes(self):
        binaries = self.base / 'bin'
        binaries.mkdir()
        for name in ('claude', 'codex', 'git'):
            executable = binaries / name
            executable.write_text('#!/bin/sh\nexit 99\n')
            executable.chmod(0o755)
        self.env['PATH'] = f'{binaries}:{self.env["PATH"]}'
        for script in ('book.sh', 'finish.sh', 'queue.sh'):
            shutil.copy(ROOT / 'scripts' / script, self.repo / 'scripts' / script)
            for name in ('../escape', "bad'name", 'bad name', ''):
                with self.subTest(script=script, name=name):
                    result = subprocess.run(['bash', str(self.repo / 'scripts' / script), name, '123'],
                                            env=self.env, capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('invalid issue name', result.stderr)
                    self.assertFalse((self.repo / 'models').exists())

    def test_book_stops_when_script_commit_fails(self):
        shutil.copy(ROOT / 'scripts/book.sh', self.repo / 'scripts/book.sh')
        issue = self.repo / 'models/example'
        issue.mkdir(parents=True)
        (issue / 'DIRECTION.md').write_text('A test direction.\n')
        (issue / 'SCRIPT.md').write_text('Ink: green\n')
        binaries = self.base / 'bin'
        binaries.mkdir()
        git = binaries / 'git'
        git.write_text('#!/bin/sh\ncase "$1" in\n'
                       'add) exit 0;;\ndiff) exit 1;;\ncommit) exit 42;;\n'
                       '*) exit 99;;\nesac\n')
        git.chmod(0o755)
        self.env['PATH'] = f'{binaries}:{self.env["PATH"]}'
        result = subprocess.run(['bash', str(self.repo / 'scripts/book.sh'), 'example'],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 42)

    def test_deploy_requires_local_config_before_build_or_network(self):
        result = self.run_deploy()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Copy wrangler.toml to wrangler.local.toml', result.stderr)

    def test_deploy_builds_then_uses_local_config(self):
        (self.repo / 'wrangler.local.toml').write_text('name = "test-gallery"\n')
        binaries = self.base / 'bin'
        binaries.mkdir()
        for name in ('python3', 'npx'):
            executable = binaries / name
            executable.write_text('#!/bin/sh\nprintf "%s\\n" "$0 $*" >> "$HOME/calls"\n')
            executable.chmod(0o755)
        Path(self.env['HOME']).mkdir()
        self.env['PATH'] = f'{binaries}:{self.env["PATH"]}'
        result = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = (Path(self.env['HOME']) / 'calls').read_text().splitlines()
        self.assertEqual(calls, [f'{binaries}/python3 scripts/site.py',
                                f'{binaries}/npx --yes wrangler@4 deploy --config wrangler.local.toml'])

    def test_cost_finds_editor_logs_for_this_checkout(self):
        shutil.copy(ROOT / 'scripts/cost.py', self.repo / 'scripts/cost.py')
        issue = self.repo / 'models' / 'example'
        issue.mkdir(parents=True)
        project_key = str(self.repo).replace('/', '-')
        logs = Path(self.env['HOME']) / '.claude/projects' / project_key / 'session/subagents'
        logs.mkdir(parents=True)
        records = [
            {'type': 'user', 'message': 'editor and writer models/example/SCRIPT.md'},
            {'type': 'assistant', 'message': {'id': 'reply', 'model': 'claude-opus-5',
             'usage': {'input_tokens': 1000, 'output_tokens': 1000}}},
        ]
        (logs / 'agent-example.jsonl').write_text('\n'.join(map(json.dumps, records)))
        result = subprocess.run(['python3', str(self.repo / 'scripts/cost.py'), 'example'],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        cost = json.loads((issue / 'COST.json').read_text())
        self.assertEqual(cost['editor']['model'], 'claude-opus-5')
        self.assertEqual(cost['editor']['usd'], 0.03)
        self.assertTrue(cost['partial'])
        self.assertIsNone(cost['draw'])


if __name__ == '__main__':
    unittest.main()
