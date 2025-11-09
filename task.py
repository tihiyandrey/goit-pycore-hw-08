from collections import UserDict
from datetime import datetime, date, timedelta
import pickle
from pathlib import Path

DATA_FILE = "addressbook.pkl"

class Field:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

class Name(Field):
    pass

class Phone(Field):
    def __init__(self, value: str):
        self._validate(value)
        super().__init__(value)

    @staticmethod
    def _validate(value: str):
        if not isinstance(value, str) or not value.isdigit() or len(value) != 10:
            raise ValueError("Phone must contain exactly 10 digits")

class Birthday(Field):
    def __init__(self, value: str):
        try:
            dt = datetime.strptime(value, "%d.%m.%Y").date()
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")
        super().__init__(dt)

    def __str__(self):
        return self.value.strftime("%d.%m.%Y")

class Record:
    def __init__(self, name: str):
        self.name = Name(name)
        self.phones: list[Phone] = []
        self.birthday: Birthday | None = None

    def add_phone(self, phone: str):
        self.phones.append(Phone(phone))

    def remove_phone(self, phone: str):
        self.phones = [p for p in self.phones if p.value != phone]

    def edit_phone(self, old_phone: str, new_phone: str):
        new_p = Phone(new_phone)
        for i, p in enumerate(self.phones):
            if p.value == old_phone:
                self.phones[i] = new_p
                return
        raise ValueError("Old phone not found")

    def find_phone(self, phone: str) -> str | None:
        for p in self.phones:
            if p.value == phone:
                return p.value
        return None

    def add_birthday(self, birthday_str: str):
        self.birthday = Birthday(birthday_str)

    def __str__(self):
        phones_str = "; ".join(p.value for p in self.phones) if self.phones else "—"
        bday = str(self.birthday) if self.birthday else "—"
        return f"Contact name: {self.name.value}, phones: {phones_str}, birthday: {bday}"

class AddressBook(UserDict):
    def add_record(self, record: Record):
        self.data[record.name.value] = record

    def find(self, name: str) -> Record | None:
        return self.data.get(name)

    def delete(self, name: str):
        self.data.pop(name, None)

    def get_upcoming_birthdays(self, days: int = 7) -> list[dict]:
        today = date.today()
        end_day = today + timedelta(days=days)
        result: list[dict] = []

        for rec in self.data.values():
            if not rec.birthday:
                continue

            bday: date = rec.birthday.value
            next_bd = bday.replace(year=today.year)

            if next_bd < today:
                next_bd = bday.replace(year=today.year + 1)

            if today <= next_bd <= end_day:
                congr_date = next_bd
                if congr_date.weekday() == 5:
                    congr_date += timedelta(days=2)
                elif congr_date.weekday() == 6:
                    congr_date += timedelta(days=1)

                result.append({
                    "name": rec.name.value,
                    "congratulation_date": congr_date.strftime("%d.%m.%Y")
                })
        result.sort(key=lambda d: datetime.strptime(d["congratulation_date"], "%d.%m.%Y"))
        return result

def save_data(book: AddressBook, filename: str = DATA_FILE) -> None:
    with open(filename, "wb") as f:
        pickle.dump(book, f)

def load_data(filename: str = DATA_FILE) -> AddressBook:
    path = Path(filename)
    if not path.exists():
        return AddressBook()
    try:
        with open(filename, "rb") as f:
            data = pickle.load(f)
            if not isinstance(data, AddressBook):
                return AddressBook()
            return data
    except (EOFError, pickle.UnpicklingError):
        return AddressBook()

def parse_input(user_input: str):
    parts = user_input.strip().split()
    if not parts:
        return "", []
    cmd, *args = parts
    return cmd.lower(), args

def input_error(func):
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyError:
            return "Contact not found."
        except ValueError as e:
            return str(e)
        except IndexError:
            return "Not enough arguments."
        except AttributeError:
            return "Contact not found."
    return inner

@input_error
def add_contact(args, book: AddressBook):
    name, phone, *_ = args
    record = book.find(name)
    message = "Contact updated."
    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."
    if phone:
        record.add_phone(phone)
    return message

@input_error
def change_contact(args, book: AddressBook):
    name, old_phone, new_phone, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError
    record.edit_phone(old_phone, new_phone)
    return "Phone updated."

@input_error
def show_phones(args, book: AddressBook):
    name, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError
    if not record.phones:
        return "No phones."
    return "; ".join(p.value for p in record.phones)

@input_error
def show_all(args, book: AddressBook):
    if not book.data:
        return "Address book is empty."
    return "\n".join(str(rec) for rec in book.data.values())

@input_error
def add_birthday(args, book: AddressBook):
    name, birthday_str, *_ = args
    record = book.find(name)
    if record is None:
        record = Record(name)
        book.add_record(record)
    record.add_birthday(birthday_str)
    return "Birthday added."

@input_error
def show_birthday(args, book: AddressBook):
    name, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError
    if not record.birthday:
        return "No birthday set."
    return str(record.birthday)

@input_error
def birthdays(args, book: AddressBook):
    upcoming = book.get_upcoming_birthdays()
    if not upcoming:
        return "No birthdays in the next 7 days."
    by_date: dict[str, list[str]] = {}
    for item in upcoming:
        by_date.setdefault(item["congratulation_date"], []).append(item["name"])
    lines = []
    for dt in sorted(by_date, key=lambda s: datetime.strptime(s, "%d.%m.%Y")):
        names = ", ".join(by_date[dt])
        lines.append(f"{dt}: {names}")
    return "\n".join(lines)

def main():
    book = load_data()
    print("Welcome to the assistant bot!")

    while True:
        user_input = input("Enter a command: ")
        command, args = parse_input(user_input)
        mutating = False

        if command in ["close", "exit"]:
            save_data(book)
            print("Good bye!")
            break

        elif command == "hello":
            print("How can I help you?")

        elif command == "add":
            print(add_contact(args, book))
            mutating = True

        elif command == "change":
            print(change_contact(args, book))
            mutating = True

        elif command == "phone":
            print(show_phones(args, book))

        elif command == "all":
            print(show_all(args, book))

        elif command == "add-birthday":
            print(add_birthday(args, book))
            mutating = True

        elif command == "show-birthday":
            print(show_birthday(args, book))

        elif command == "birthdays":
            print(birthdays(args, book))

        else:
            print("Invalid command.")

        if mutating:
            save_data(book)
