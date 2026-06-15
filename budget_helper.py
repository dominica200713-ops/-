from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DATA_FILE = Path("data.csv")


@dataclass
class Expense:
    day: int
    amount: float
    category: str
    comment: str = ""


class TreeNode:
    def __init__(self, expense: Expense) -> None:
        self.expense = expense
        self.left: Optional[TreeNode] = None
        self.right: Optional[TreeNode] = None


class ExpenseTree:
    def __init__(self) -> None:
        self.root: Optional[TreeNode] = None

    def clear(self) -> None:
        self.root = None

    def add(self, expense: Expense) -> None:
        self.root = self._add_node(self.root, expense)

    def _add_node(self, node: Optional[TreeNode], expense: Expense) -> TreeNode:
        if node is None:
            return TreeNode(expense)

        if expense.day < node.expense.day:
            node.left = self._add_node(node.left, expense)
        else:
            node.right = self._add_node(node.right, expense)

        return node

    def inorder(self) -> list[Expense]:
        result: list[Expense] = []
        self._inorder(self.root, result)
        return result

    def _inorder(self, node: Optional[TreeNode], result: list[Expense]) -> None:
        if node is None:
            return
        self._inorder(node.left, result)
        result.append(node.expense)
        self._inorder(node.right, result)

    def preorder_days(self) -> list[int]:
        result: list[int] = []
        self._preorder(self.root, result)
        return result

    def _preorder(self, node: Optional[TreeNode], result: list[int]) -> None:
        if node is None:
            return
        result.append(node.expense.day)
        self._preorder(node.left, result)
        self._preorder(node.right, result)


class BudgetManager:
    def __init__(self) -> None:
        self.expenses: list[Expense] = []
        self.undo_stack: list[Expense] = []
        self.daily_totals = [0.0] * 32
        self.prefix = [0.0] * 32
        self.tree = ExpenseTree()

    def add_expense(self, day: int, amount: float, category: str, comment: str = "") -> Expense:
        if day < 1 or day > 31:
            raise ValueError("День должен быть от 1 до 31.")
        if amount <= 0:
            raise ValueError("Сумма должна быть больше нуля.")
        if not category:
            raise ValueError("Категория не должна быть пустой.")

        expense = Expense(day, amount, category, comment)
        self.expenses.append(expense)
        self.undo_stack.append(expense)
        self._rebuild()
        return expense

    def get_all_expenses(self) -> list[Expense]:
        return self.expenses.copy()

    def undo_last_add(self) -> Optional[Expense]:
        if not self.undo_stack:
            return None

        expense = self.undo_stack.pop()
        self.expenses.remove(expense)
        self._rebuild()
        return expense

    def period_sum(self, start: int, end: int) -> float:
        if start < 1 or end > 31 or start > end:
            raise ValueError("Период должен быть в пределах 1-31, начало не больше конца.")
        return self.prefix[end] - self.prefix[start - 1]

    def max_expense_day(self) -> tuple[int, float]:
        max_day = 1
        max_amount = self.daily_totals[1]

        for day in range(2, 32):
            if self.daily_totals[day] > max_amount:
                max_day = day
                max_amount = self.daily_totals[day]

        return max_day, max_amount

    def category_totals_sorted(self) -> list[tuple[str, float]]:
        totals: dict[str, float] = {}

        for expense in self.expenses:
            totals[expense.category] = totals.get(expense.category, 0.0) + expense.amount

        items = list(totals.items())

        # простая сортировка вставками по убыванию суммы
        for i in range(1, len(items)):
            current = items[i]
            j = i - 1
            while j >= 0 and items[j][1] < current[1]:
                items[j + 1] = items[j]
                j -= 1
            items[j + 1] = current

        return items

    def tree_inorder_expenses(self) -> list[Expense]:
        return self.tree.inorder()

    def tree_preorder_days(self) -> list[int]:
        return self.tree.preorder_days()

    def load_csv(self, path: str | Path) -> int:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Файл не найден: {path}")

        with path.open("r", encoding="utf-8-sig", newline="") as file:
            sample = file.read(1024)
            file.seek(0)
            delimiter = ";" if ";" in sample else ","
            reader = csv.DictReader(file, delimiter=delimiter)

            loaded: list[Expense] = []
            for row in reader:
                day = int(row.get("day", row.get("День", "0")))
                amount_text = row.get("amount", row.get("Сумма", "0")).replace(",", ".")
                amount = float(amount_text)
                category = row.get("category", row.get("Категория", "")).strip()
                comment = row.get("comment", row.get("Комментарий", "")).strip()

                if day < 1 or day > 31:
                    raise ValueError("В CSV есть день вне диапазона 1-31.")
                if amount <= 0:
                    raise ValueError("В CSV есть сумма меньше или равная нулю.")
                if not category:
                    raise ValueError("В CSV есть пустая категория.")

                loaded.append(Expense(day, amount, category, comment))

        self.expenses = loaded
        self.undo_stack = loaded.copy()
        self._rebuild()
        return len(loaded)

    def save_csv(self, path: str | Path) -> None:
        path = Path(path)
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(["day", "amount", "category", "comment"])
            for expense in self.expenses:
                writer.writerow([expense.day, expense.amount, expense.category, expense.comment])

    def _rebuild(self) -> None:
        self.daily_totals = [0.0] * 32
        self.prefix = [0.0] * 32
        self.tree.clear()

        for expense in self.expenses:
            self.daily_totals[expense.day] += expense.amount
            self.tree.add(expense)

        for day in range(1, 32):
            self.prefix[day] = self.prefix[day - 1] + self.daily_totals[day]


def print_menu() -> None:
    print("\nБЮДЖЕТНЫЙ ПОМОЩНИК")
    print("1. Добавить расход")
    print("2. Показать все расходы")
    print("3. Посчитать расходы за период")
    print("4. Найти день с максимальным расходом")
    print("5. Показать категории по сумме трат")
    print("6. Отменить последнее добавление")
    print("7. Показать расходы через дерево")
    print("8. Загрузить расходы из CSV")
    print("9. Сохранить расходы в CSV")
    print("10. Показать прямой обход дерева")
    print("0. Выход")


def format_expense(expense: Expense) -> str:
    comment = f" | {expense.comment}" if expense.comment else ""
    return f"{expense.day:02d} число | {expense.amount:.2f} руб. | {expense.category}{comment}"


def input_int(prompt: str) -> int:
    while True:
        try:
            return int(input(prompt).strip())
        except ValueError:
            print("Ошибка: введите целое число.")


def input_float(prompt: str) -> float:
    while True:
        try:
            return float(input(prompt).strip().replace(",", "."))
        except ValueError:
            print("Ошибка: введите число.")


def add_expense_ui(manager: BudgetManager) -> None:
    try:
        day = input_int("День месяца [1-31]: ")
        amount = input_float("Сумма расхода: ")
        category = input("Категория: ").strip()
        comment = input("Комментарий, можно пусто: ").strip()
        expense = manager.add_expense(day, amount, category, comment)
        print("Расход добавлен:", format_expense(expense))
    except ValueError as error:
        print(f"Ошибка: {error}")


def show_all_expenses(manager: BudgetManager) -> None:
    expenses = manager.get_all_expenses()
    if not expenses:
        print("Пока расходов нет.")
        return

    print("\nВсе расходы:")
    for number, expense in enumerate(expenses, start=1):
        print(f"{number}. {format_expense(expense)}")


def show_period_sum(manager: BudgetManager) -> None:
    try:
        start = input_int("Начальный день: ")
        end = input_int("Конечный день: ")
        total = manager.period_sum(start, end)
        print(f"Расходы с {start} по {end} число: {total:.2f} руб.")
        print("Расчёт выполнен через префиксные суммы за O(1).")
    except ValueError as error:
        print(f"Ошибка: {error}")


def show_max_day(manager: BudgetManager) -> None:
    day, amount = manager.max_expense_day()
    if amount == 0:
        print("Расходов пока нет.")
    else:
        print(f"Максимальный расход был {day} числа: {amount:.2f} руб.")
        print("Алгоритм: линейный поиск по массиву расходов за дни месяца.")


def show_categories(manager: BudgetManager) -> None:
    categories = manager.category_totals_sorted()
    if not categories:
        print("Категорий пока нет.")
        return

    print("\nКатегории по убыванию расходов:")
    for number, (category, total) in enumerate(categories, start=1):
        print(f"{number}. {category}: {total:.2f} руб.")
    print("Алгоритм сортировки: сортировка вставками.")


def undo_last(manager: BudgetManager) -> None:
    expense = manager.undo_last_add()
    if expense is None:
        print("Стек отмены пуст. Отменять нечего.")
    else:
        print("Последний расход отменён:", format_expense(expense))


def show_tree(manager: BudgetManager) -> None:
    expenses = manager.tree_inorder_expenses()
    if not expenses:
        print("Дерево пустое.")
        return

    print("\nРасходы через симметричный рекурсивный обход дерева:")
    for expense in expenses:
        print(format_expense(expense))


def load_csv_ui(manager: BudgetManager) -> None:
    path = input(f"Путь к CSV-файлу [{DATA_FILE}]: ").strip() or str(DATA_FILE)
    try:
        count = manager.load_csv(path)
        print(f"Загружено записей: {count}")
    except (ValueError, FileNotFoundError) as error:
        print(f"Ошибка: {error}")


def save_csv_ui(manager: BudgetManager) -> None:
    path = input(f"Путь для сохранения CSV [{DATA_FILE}]: ").strip() or str(DATA_FILE)
    manager.save_csv(path)
    print(f"Данные сохранены в файл: {path}")


def show_preorder(manager: BudgetManager) -> None:
    days = manager.tree_preorder_days()
    if not days:
        print("Дерево пустое.")
    else:
        print("Прямой рекурсивный обход дерева по дням:", " -> ".join(map(str, days)))


def main() -> None:
    manager = BudgetManager()

    while True:
        print_menu()
        choice = input("Выберите действие: ").strip()

        if choice == "1":
            add_expense_ui(manager)
        elif choice == "2":
            show_all_expenses(manager)
        elif choice == "3":
            show_period_sum(manager)
        elif choice == "4":
            show_max_day(manager)
        elif choice == "5":
            show_categories(manager)
        elif choice == "6":
            undo_last(manager)
        elif choice == "7":
            show_tree(manager)
        elif choice == "8":
            load_csv_ui(manager)
        elif choice == "9":
            save_csv_ui(manager)
        elif choice == "10":
            show_preorder(manager)
        elif choice == "0":
            print("Работа завершена.")
            break
        else:
            print("Неизвестная команда. Попробуйте снова.")


if __name__ == "__main__":
    main()
