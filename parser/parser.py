from os import environ as env
import csv
from pathlib import Path
from typing import List, Iterable
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.results import InsertManyResult
from rich.console import Console  # Note: `rich` is installed as part of `typer[all]`
import typer

# Create a `Console` instance, which I can use to print fancy messages to the console.
console = Console()

# Load variables defined in the `.env` file, into the `os.environ` dictionary.
# Note: Existing environment variables get priority; i.e. won't be overridden.
# Reference: https://github.com/theskumar/python-dotenv#getting-started
load_dotenv(verbose=True)

# Names of columns whose values this script will use verbatim (i.e. will not sanitize).
METADATA_COLUMN_NAMES = ["Study_Code", "Sample_ID"]


def is_at_least_zero_when_float(s: str) -> bool:
    """
    Checks whether the specified string, when parsed as a float, is >= 0.

    :param s: The string you want to check (e.g. "123", "-1.23")
    :return: `True` if the equivalent float is >= 0; otherwise, `False`
    """
    result = False  # assume `False` until proven otherwise
    try:
        result = True if float(s) >= 0 else False
    except (TypeError, ValueError, OverflowError):
        pass
    return result


def parse_csv_file(file_path: Path) -> List[dict]:
    """
    Parses the specified CSV file into a list of dictionaries.

    :param file_path: Absolute path to CSV file
    :return: List of dictionaries, each of which represents a row of data
    """
    sanitized_rows: List[dict] = []

    with open(file_path, newline="") as f:
        # Parse each row of the CSV file (except the first row) into a dictionary,
        # using the column names from the first row as the dictionary's keys.
        dict_reader: Iterable[dict] = csv.DictReader(f)
        for row in dict_reader:
            # Build a "sanitized" dictionary based upon this row (i.e. a dictionary
            # in which invalid values from this row are represented by `None`).
            #
            # Note: A value is invalid unless either:
            #       (a) it is in a metadata column (e.g. the "Sample_ID" column), or
            #       (b) when parsed as a float, it is >= 0 (e.g. "-1" is invalid).
            #
            sanitized_row = dict()
            for col_name, raw_value in row.items():
                if col_name in METADATA_COLUMN_NAMES:
                    sanitized_row[col_name] = raw_value  # use as-is
                elif is_at_least_zero_when_float(raw_value):
                    sanitized_row[col_name] = raw_value  # use as-is
                else:
                    sanitized_row[col_name] = None  # use `None`

            sanitized_rows.append(sanitized_row)

    return sanitized_rows


def store_samples_in_database(samples: List[dict]) -> InsertManyResult:
    """
    Stores samples in the MongoDB database specified by environment variables.

    :param samples: List of dictionaries, each of which represents a sample
    :return: MongoDB `InsertManyResult`
    """

    # Insert the data into the database.
    #
    # Note: If the specified database and/or collection don't already exist when they are used,
    #       they will be automatically created at that time.
    #       Reference: https://pymongo.readthedocs.io/en/stable/tutorial.html
    #
    mongo_client: MongoClient = MongoClient(
        username=env["MONGO_USERNAME"],
        password=env["MONGO_PASSWORD"],
        host=env["MONGO_HOST"],
        port=int(env["MONGO_PORT"]),
    )
    db = mongo_client[env["MONGO_DATABASE_NAME"]]
    collection = db[env["MONGO_COLLECTION_NAME"]]

    # Create an index of the "Sample_ID" values, since the web server will query by those values.
    collection.create_index([("Sample_ID", ASCENDING)])

    # Create a (compound) unique index of the two metadata columns, to prevent data duplication
    # in case, for example, this script gets run multiple times (i.e. re-processes the same file).
    collection.create_index(
        [("Sample_ID", ASCENDING), ("Study_Code", ASCENDING)], unique=True
    )

    # Insert the samples.
    #
    # Note: This raises a `pymongo.errors.BulkWriteError` exception if any of the items being
    #       inserted violate the unique index.
    #
    ids = collection.insert_many(samples)
    return ids


def main(
    # Validate the argument as a path to a readable file, using validators built into Typer.
    # Reference: https://typer.tiangolo.com/tutorial/parameter-types/path/#path-validations
    csv_file_path: Path = typer.Argument(
        ...,  # has no default value (i.e. user must provide one)
        help="The relative or absolute path to the CSV file.",
        exists=True,  # necessary in order to use the validators below
        file_okay=True,  # path can point to a file
        dir_okay=False,  # path cannot point to a folder
        readable=True,  # script can read the file
        resolve_path=True,  # convert path into an absolute path
    ),
    is_debugging: bool = typer.Option(
        False, "--debug", "-d", help="Enable debug output."
    ),
):
    """Extracts data from a CSV file and stores that data in a database."""
    if is_debugging:
        console.log(f"CSV file: {csv_file_path}")

    samples = parse_csv_file(csv_file_path)
    console.print(f"Extracted {len(samples)} samples from the CSV file.")
    if is_debugging:
        console.log(samples)

    result = store_samples_in_database(samples)
    console.print(f"Stored {len(result.inserted_ids)} samples in the database.")
    if is_debugging:
        console.log(result.inserted_ids)


if __name__ == "__main__":
    typer.run(main)
