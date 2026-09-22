import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from tasks import TaskStore, main


class TaskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "data" / "tasks.json"
        self.store = TaskStore(self.path)

    def test_add_persists_unicode(self):
        self.store.add("  Купить   молоко  ")
        self.assertEqual(TaskStore(self.path).load()["tasks"],
                         [{"id": 1, "title": "Купить молоко", "done": False}])

    def test_empty_title_creates_no_file(self):
        with self.assertRaises(ValueError):
            self.store.add(" \n ")
        self.assertFalse(self.path.exists())

    def test_complete_and_reopen(self):
        self.store.add("Read")
        self.store.update(1, "done")
        self.assertTrue(self.store.load()["tasks"][0]["done"])
        self.store.update(1, "undo")
        self.assertFalse(self.store.load()["tasks"][0]["done"])

    def test_deleted_ids_are_not_reused(self):
        self.store.add("First")
        self.store.update(1, "delete")
        self.assertEqual(self.store.add("Second")["id"], 2)

    def test_unknown_id_preserves_file(self):
        self.store.add("Keep")
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.store.update(999, "delete")
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_data_is_not_overwritten(self):
        self.path.parent.mkdir()
        for broken in ['{oops', '[]', '{"next_id": 1, "tasks": [{}]}']:
            self.path.write_text(broken, encoding="utf-8")
            with self.assertRaises(ValueError):
                self.store.add("New")
            self.assertEqual(self.path.read_text(encoding="utf-8"), broken)

    def test_cli_filters_completed_tasks(self):
        self.store.add("Alpha")
        self.store.add("Beta")
        self.store.update(1, "done")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main(["--file", str(self.path), "list", "--status", "active"])
        self.assertIn("Beta", output.getvalue())
        self.assertNotIn("Alpha", output.getvalue())

    def test_cli_reports_missing_task(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
            main(["--file", str(self.path), "done", "12"])
        self.assertEqual(result.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
