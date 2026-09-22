"""Tiny Tasks: a small, dependency-free command-line task list."""

import argparse
import json
import os
from pathlib import Path
import tempfile


class TaskStore:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            return {"next_id": 1, "tasks": []}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("invalid format")
            tasks = data.get("tasks")
            next_id = data.get("next_id")
            if not isinstance(tasks, list) or type(next_id) is not int or next_id < 1:
                raise ValueError("invalid format")
            ids = set()
            for task in tasks:
                if (not isinstance(task, dict)
                        or type(task.get("id")) is not int
                        or not 0 < task["id"] < next_id
                        or task["id"] in ids
                        or not isinstance(task.get("title"), str)
                        or not task["title"].strip()
                        or type(task.get("done")) is not bool):
                    raise ValueError("invalid task")
                ids.add(task["id"])
            return data
        except (ValueError, UnicodeError) as exc:
            raise ValueError(f"Файл задач повреждён: {self.path}. Сохраните копию и проверьте JSON.") from exc

    def save(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent,
                prefix=".tasks-", suffix=".tmp", delete=False
            ) as stream:
                temp_path = Path(stream.name)
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, self.path)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def add(self, title):
        title = " ".join(title.split())
        if not title:
            raise ValueError("Название задачи не может быть пустым.")
        data = self.load()
        task = {"id": data["next_id"], "title": title, "done": False}
        data["tasks"].append(task)
        data["next_id"] += 1
        self.save(data)
        return task

    def update(self, task_id, action):
        if action not in {"done", "undo", "delete"}:
            raise ValueError("Неизвестное действие.")
        data = self.load()
        for task in data["tasks"]:
            if task["id"] == task_id:
                if action == "delete":
                    data["tasks"].remove(task)
                else:
                    task["done"] = action == "done"
                self.save(data)
                return task
        raise ValueError(f"Задача #{task_id} не найдена.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Tiny Tasks — список задач в терминале.")
    parser.add_argument("--file", type=Path,
                        default=Path(__file__).resolve().parent / "data" / "tasks.json",
                        help="путь к JSON-файлу (по умолчанию data/tasks.json рядом со скриптом)")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="добавить задачу")
    add.add_argument("title", help='название задачи в кавычках')
    listing = commands.add_parser("list", help="показать задачи")
    listing.add_argument("--status", choices=["all", "active", "done"], default="all")
    for name, help_text in [("done", "завершить задачу"), ("undo", "вернуть в работу"),
                            ("delete", "удалить задачу")]:
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("id", type=int, help="номер задачи")
    args = parser.parse_args(argv)
    store = TaskStore(args.file)
    try:
        if args.command == "add":
            task = store.add(args.title)
            print(f"Добавлена задача #{task['id']}: {task['title']}")
        elif args.command == "list":
            tasks = store.load()["tasks"]
            selected = [task for task in tasks if args.status == "all"
                        or task["done"] == (args.status == "done")]
            if not selected:
                print("Задач нет. Добавьте первую: python tasks.py add \"Моя задача\"")
            for task in selected:
                mark = "x" if task["done"] else " "
                print(f"[{mark}] #{task['id']}  {task['title']}")
        else:
            task = store.update(args.id, args.command)
            verb = {"done": "Завершена", "undo": "Возвращена в работу", "delete": "Удалена"}
            print(f"{verb[args.command]} задача #{task['id']}: {task['title']}")
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Ошибка: {exc}\n")


if __name__ == "__main__":
    main()
