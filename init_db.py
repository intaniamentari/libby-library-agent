"""Create (or reset) the sample library database.

Usage:
    python init_db.py           # create library.db if it doesn't exist yet
    python init_db.py --reset   # delete and recreate library.db with fresh sample data
"""
import argparse
import os
import sqlite3

DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "library.db")

SCHEMA = """
PRAGMA foreign_keys = ON;

-- Where books are stored
CREATE TABLE IF NOT EXISTS locations (
    location_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room        VARCHAR(100) NOT NULL,
    shelf       VARCHAR(50)  NOT NULL,
    UNIQUE (room, shelf)
);

-- Library staff
CREATE TABLE IF NOT EXISTS librarians (
    librarian_id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name   VARCHAR(255) NOT NULL,
    last_name    VARCHAR(255) NOT NULL
);

-- Library members
CREATE TABLE IF NOT EXISTS readers (
    reader_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name VARCHAR(255) NOT NULL,
    last_name  VARCHAR(255) NOT NULL,
    email      VARCHAR(255) UNIQUE,
    phone      VARCHAR(50)
);

-- Books, with their location and current status
CREATE TABLE IF NOT EXISTS books (
    book_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    title          VARCHAR(255) NOT NULL,
    author         VARCHAR(255) NOT NULL,
    isbn           VARCHAR(20) UNIQUE,
    published_year INTEGER,
    location_id    INTEGER NOT NULL,
    status         VARCHAR(20) NOT NULL DEFAULT 'available'
                   CHECK (status IN ('available', 'borrowed')),
    FOREIGN KEY (location_id) REFERENCES locations (location_id)
);

-- Borrowing history: who borrowed which book, handled by which librarian
CREATE TABLE IF NOT EXISTS loans (
    loan_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id      INTEGER NOT NULL,
    reader_id    INTEGER NOT NULL,
    librarian_id INTEGER NOT NULL,
    borrow_date  DATE NOT NULL DEFAULT (DATE('now')),
    due_date     DATE NOT NULL,
    return_date  DATE,                -- NULL = not returned yet
    FOREIGN KEY (book_id)      REFERENCES books (book_id),
    FOREIGN KEY (reader_id)    REFERENCES readers (reader_id),
    FOREIGN KEY (librarian_id) REFERENCES librarians (librarian_id)
);

-- A book can only have one open (unreturned) loan at a time
CREATE UNIQUE INDEX IF NOT EXISTS one_open_loan_per_book
    ON loans (book_id) WHERE return_date IS NULL;
"""

SEED = """
INSERT INTO locations (room, shelf) VALUES
    ('Main Hall', 'A1'),
    ('Main Hall', 'A2'),
    ('Reading Room', 'B1');

INSERT INTO librarians (first_name, last_name) VALUES
    ('Alice', 'Smith'),
    ('Bob', 'Johnson');

INSERT INTO readers (first_name, last_name, email, phone) VALUES
    ('David', 'Lee',   'david@example.com', '0811-111-111'),
    ('Emily', 'Chen',  'emily@example.com', '0812-222-222'),
    ('Frank', 'Brown', 'frank@example.com', '0813-333-333');

INSERT INTO books (title, author, isbn, published_year, location_id) VALUES
    ('Clean Code',                          'Robert C. Martin',           '9780132350884', 2008, 1),
    ('The Pragmatic Programmer',            'Hunt & Thomas',              '9780135957059', 2019, 1),
    ('Database System Concepts',            'Silberschatz',               '9780078022159', 2019, 2),
    ('Laskar Pelangi',                      'Andrea Hirata',              '9789793062792', 2005, 3),
    ('The Answer',                          'Anderson Jeremy',            '9780000000001', 2005, 3),
    ('Refactoring',                         'Martin Fowler',              '9780000000002', 2018, 1),
    ('Design Patterns',                     'Gamma, Helm, Johnson, Vlissides', '9780000000003', 1994, 1),
    ('Introduction to Algorithms',          'Cormen et al.',              '9780000000004', 2009, 2),
    ('Code Complete',                       'Steve McConnell',            '9780000000005', 2004, 1),
    ('The Mythical Man-Month',              'Fred Brooks',                '9780000000006', 1975, 2),
    ('Structure and Interpretation of Computer Programs', 'Abelson & Sussman', '9780000000007', 1996, 2),
    ('Eloquent JavaScript',                 'Marijn Haverbeke',           '9780000000008', 2018, 1),
    ('Python Crash Course',                 'Eric Matthes',               '9780000000009', 2019, 1),
    ('Designing Data-Intensive Applications','Martin Kleppmann',          '9780000000010', 2017, 2),
    ('SQL Antipatterns',                    'Bill Karwin',                '9780000000011', 2010, 2),
    ('Bumi Manusia',                        'Pramoedya Ananta Toer',      '9780000000012', 1980, 3),
    ('Anak Semua Bangsa',                   'Pramoedya Ananta Toer',      '9780000000013', 1980, 3),
    ('Ronggeng Dukuh Paruk',                'Ahmad Tohari',               '9780000000014', 1982, 3),
    ('Cantik Itu Luka',                     'Eka Kurniawan',              '9780000000015', 2002, 3),
    ('Negeri 5 Menara',                     'Ahmad Fuadi',                '9780000000016', 2009, 3),
    ('Sang Pemimpi',                        'Andrea Hirata',              '9780000000017', 2006, 3),
    ('Ayat-Ayat Cinta',                     'Habiburrahman El Shirazy',   '9780000000018', 2004, 3),
    ('Pulang',                              'Leila S. Chudori',           '9780000000019', 2012, 3),
    ('Sapiens',                             'Yuval Noah Harari',          '9780000000020', 2011, 2),
    ('Atomic Habits',                       'James Clear',                '9780000000021', 2018, 2);

-- David borrows book 1 (handled by Alice), Emily borrows book 3 (handled by Bob)
INSERT INTO loans (book_id, reader_id, librarian_id, borrow_date, due_date) VALUES
    (1, 1, 1, '2026-10-20', '2026-11-03'),
    (3, 2, 2, '2026-10-22', '2026-11-05');

UPDATE books SET status = 'borrowed' WHERE book_id IN (1, 3);
"""


def create_database(db_path: str = DEFAULT_DB, reset: bool = False) -> None:
    """Create the schema and insert sample data (only if the tables are empty)."""
    if reset and os.path.exists(db_path):
        os.remove(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        has_data = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0] > 0
        if not has_data:
            conn.executescript(SEED)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create the sample library database.")
    parser.add_argument("--reset", action="store_true", help="delete and recreate the database")
    parser.add_argument("--db", default=DEFAULT_DB, help="path to the SQLite file")
    args = parser.parse_args()

    create_database(args.db, reset=args.reset)
    print(f"Database ready: {args.db}")
