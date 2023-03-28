from os import environ as env
import csv
import re
from pathlib import Path
from typing import List, Dict, Iterable, Optional, TypeAlias

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, errors
from rich.console import Console  # Note: `rich` is installed as part of `typer[all]`
import typer

# Create a `Console` instance, which I can use to print fancy messages to the console.
console = Console()

# Load variables defined in the `.env` file, into the `os.environ` dictionary.
# Note: Existing environment variables get priority; i.e. won't be overridden.
# Reference: https://github.com/theskumar/python-dotenv#getting-started
load_dotenv(verbose=True)

# Type alias for a dictionary created from a row of a CSV file.
RowDict: TypeAlias = Dict[str, Optional[str]]

# Names of columns whose values this script will use verbatim (i.e. will not sanitize).
METADATA_COLUMN_NAMES = ["Study_Code", "Sample_ID"]


# Regular expression this script can use to validate data extracted from data columns.
# Note: Matches "1", "2.", "3.4", ".5", "0.67890", etc.; and does not match "." alone.
VALID_DATA_REGEX = re.compile(r"^\d+\.?\d*$|^\.?\d+$")


def sanitize_metadata_value(raw_value: Optional[str]) -> Optional[str]:
    """
    Returns a sanitized version of a value originating in a metadata column of a CSV file.

    Sanitization rules:
    - If the raw value is not a string, it will be sanitized to `None`.
    - If the raw string has leading/trailing whitespace, that whitespace will be removed.

    :param raw_value: The raw value you want to sanitize
    :return: The sanitized value
    """
    if type(raw_value) is str:
        stripped_str = raw_value.strip()
        return stripped_str
    else:
        return None


def sanitize_data_value(raw_value: Optional[str]) -> Optional[str]:
    """
    Returns a sanitized version of a value originating in a data column of a CSV file.

    Sanitization rules:
    - If the raw value is not a string, it will be sanitized to `None`.
    - If the raw string has leading/trailing whitespace, that whitespace will be removed.
    - If the remaining string does not consist solely of a number equal to or greater than 0,
      the string will be sanitized to `None`.

    :param raw_value: The raw value you want to sanitize
    :return: The sanitized value
    """
    if type(raw_value) is str:
        stripped_str = raw_value.strip()
        return stripped_str if VALID_DATA_REGEX.match(stripped_str) else None
    else:
        return None


def parse_csv_file(file_path: Path) -> List[RowDict]:
    """
    Parses the specified CSV file into a list of sanitary dictionaries.

    :param file_path: Absolute path to CSV file
    :return: List of dictionaries, each of which represents a row of data
    """
    sanitary_rows = []

    with open(file_path, newline="") as f:
        # Parse each row of the CSV file (except the first row) into a dictionary,
        # using the column names from the first row as the dictionary's keys.
        dict_reader: Iterable[RowDict] = csv.DictReader(f)
        for row_dict in dict_reader:
            # Build a "sanitized" dictionary based upon this row.
            sanitary_row = {}
            for column_name, value in row_dict.items():
                if column_name in METADATA_COLUMN_NAMES:
                    sanitary_row[column_name] = sanitize_metadata_value(value)
                else:
                    sanitary_row[column_name] = sanitize_data_value(value)
            sanitary_rows.append(sanitary_row)

    return sanitary_rows


def store_samples_in_database(samples: List[dict]) -> List[int]:
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

    # Insert the samples into the collection.
    #
    # Note: An earlier version of this script used the `collection.insert_many` function to insert
    #       all samples into the collection in bulk. If any of those samples violated the "unique"
    #       index in the collection, the function would raise a `pymongo.errors.BulkWriteError`
    #       exception and the remaining samples would not be inserted. While that exception object
    #       does contain a property named `nInserted` (which I suspect indicates the number of
    #       records that were successfully inserted), I failed to find official documentation
    #       about that property. So, I am hesitant to rely on it. However, I still want to be able
    #       to display an actionable error message. For that reason, I updated this script to perform
    #       the inserts one by one (trading performance for usability), relying only on features
    #       about which I found official documentation.
    #
    #       References:
    #       - https://pymongo.readthedocs.io/en/stable/api/pymongo/errors.html#pymongo.errors.BulkWriteError
    #       - https://pymongo.readthedocs.io/en/stable/api/pymongo/results.html#pymongo.results.BulkWriteResult.inserted_count
    #       - https://github.com/mongodb/mongo-python-driver/blob/065b02bcb3ff6d8c088e4934105b9158f48d7074/pymongo/bulk.py#L98
    #
    inserted_ids: List[int] = []
    for sample in samples:
        try:
            result = collection.insert_one(sample)
            inserted_ids.append(result.inserted_id)
        except errors.WriteError:
            console.print(f"[red]Failed[/red] to store sample in database: {sample}")

    return inserted_ids


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

    inserted_ids = store_samples_in_database(samples)
    console.print(f"Stored {len(inserted_ids)} samples in the database.")
    if is_debugging:
        console.log(inserted_ids)


if __name__ == "__main__":
    typer.run(main)
