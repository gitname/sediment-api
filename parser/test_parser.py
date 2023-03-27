from os import environ as env
from tempfile import NamedTemporaryFile
from pathlib import Path
from typing import List, Iterator
from pymongo import MongoClient
import pymongo.errors
import pytest
from .parser import (
    parse_csv_file,
    is_at_least_zero_when_float,
    store_samples_in_database,
)


@pytest.fixture
def example_samples() -> List[dict]:
    """Returns a list of samples that can be used in tests."""
    samples = [
        {
            "Study_Code": "WHONDRS_S19S",
            "Sample_ID": "S19S_0001_BULK-D",
            "Percent_Fine_Sand": "21.1",
            "Percent_Med_Sand": "69.7",
            "Percent_Coarse_Sand": "0.1",
            "Percent_Tot_Sand": "90.9",
            "Percent_Clay": "0",
            "Percent_Silt": "9.1",
        },
        {
            "Study_Code": "WHONDRS_S19S",
            "Sample_ID": "S19S_0001_BULK-M",
            "Percent_Fine_Sand": "65.3",
            "Percent_Med_Sand": "26",
            "Percent_Coarse_Sand": "0.6",
            "Percent_Tot_Sand": "91.9",
            "Percent_Clay": "6.9",
            "Percent_Silt": "1.2",
        },
        {
            "Study_Code": "WHONDRS_S19S",
            "Sample_ID": "S19S_0001_BULK-U",
            "Percent_Fine_Sand": "20.4",
            "Percent_Med_Sand": "68.6",
            "Percent_Coarse_Sand": "2.1",
            "Percent_Tot_Sand": "91.1",
            "Percent_Clay": "8.9",
            "Percent_Silt": "0",
        },
    ]

    return samples


@pytest.fixture
def db_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[MongoClient]:
    """
    Patches the database name environment variable to refer to a test database.
    Yields a MongoDB client.
    Deletes the test database after the dependent test ends.
    """
    # Patch a specific environment variable so both the test and the app-under-test use a temporary database.
    # Reference: https://docs.pytest.org/en/stable/how-to/monkeypatch.html#monkeypatching-environment-variables
    db_name = "_test"
    monkeypatch.setenv("MONGO_DATABASE_NAME", db_name)

    mongo_client: MongoClient = MongoClient(
        username=env["MONGO_USERNAME"],
        password=env["MONGO_PASSWORD"],
        host=env["MONGO_HOST"],
        port=int(env["MONGO_PORT"]),
    )

    yield mongo_client

    # Delete the database.
    mongo_client.drop_database(db_name)


@pytest.fixture
def temp_file_path() -> Iterator[Path]:
    """
    Creates a closed, empty, temporary file.
    Yields the path to the file.
    Deletes the file after the dependent test ends.
    """
    # Create a temporary file that does not automatically get deleted when closed.
    # Reference: https://docs.python.org/3/library/tempfile.html#tempfile.NamedTemporaryFile
    file = NamedTemporaryFile(delete=False)
    file.close()
    file_path = Path(file.name)

    yield file_path

    # Delete the file.
    Path.unlink(file_path)


class TestParseCsvFile:
    def test_it_preserves_column_names_verbatim(self, temp_file_path):
        # Populate the CSV file.
        with open(temp_file_path, "w") as f:
            print("""AAA, 12-3 4. ,ccc\n1,2,3""", file=f)

        # Parse it into samples and compare to expectation.
        samples = parse_csv_file(temp_file_path)
        assert samples[0] == {
            "AAA": "1",
            " 12-3 4. ": "2",
            "ccc": "3",
        }

    def test_it_preserves_metadata_values_verbatim(self, temp_file_path):
        # Populate the CSV file.
        with open(temp_file_path, "w") as f:
            print("""Study_Code,Sample_ID,C\naaa, 12-3 4. ,3""", file=f)

        # Parse it into samples and compare to expectation.
        samples = parse_csv_file(temp_file_path)
        assert samples[0] == {
            "Study_Code": "aaa",
            "Sample_ID": " 12-3 4. ",
            "C": "3",
        }

    def test_it_nullifies_invalid_data_values(self, temp_file_path):
        # Populate the CSV file.
        with open(temp_file_path, "w") as f:
            print(
                """Study_Code,Sample_ID,C,D,E,F,G,H,I,J\n"""
                + """x,y,0,0.1,1,1.,1e2,z,-0.1,-9999""",
                file=f,
            )

        # Parse it into samples and compare to expectation.
        samples = parse_csv_file(temp_file_path)
        assert samples[0] == {
            "Study_Code": "x",
            "Sample_ID": "y",
            "C": "0",
            "D": "0.1",
            "E": "1",
            "F": "1.",
            "G": "1e2",
            "H": None,  # raw value: "z"
            "I": None,  # raw value: "-0.1"
            "J": None,  # raw value: "-9999"
        }

    def test_it_parses_data_rows_into_samples(self, temp_file_path):
        # Populate the CSV file.
        with open(temp_file_path, "w") as f:
            print(
                """Study_Code,Sample_ID,Percent_Fine_Sand,Percent_Med_Sand,"""
                + """Percent_Coarse_Sand,Percent_Tot_Sand,Percent_Clay,Percent_Silt\n"""
                # ------------------------------------------------------------------- # end of headers
                + """WHONDRS_S19S,S19S_0001_BULK-D,21.1,69.7,0.1,90.9,0,9.1\n"""
                + """WHONDRS_S19S,S19S_0001_BULK-M,65.3,26,0.6,91.9,6.9,1.2\n"""
                + """WHONDRS_S19S,S19S_0001_BULK-U,20.4,68.6,2.1,91.1,8.9,0""",
                file=f,
            )

        # Parse it into samples and compare to expectation.
        samples = parse_csv_file(temp_file_path)
        assert len(samples) == 3
        assert samples[0] == {
            "Study_Code": "WHONDRS_S19S",
            "Sample_ID": "S19S_0001_BULK-D",
            "Percent_Fine_Sand": "21.1",
            "Percent_Med_Sand": "69.7",
            "Percent_Coarse_Sand": "0.1",
            "Percent_Tot_Sand": "90.9",
            "Percent_Clay": "0",
            "Percent_Silt": "9.1",
        }
        assert samples[1] == {
            "Study_Code": "WHONDRS_S19S",
            "Sample_ID": "S19S_0001_BULK-M",
            "Percent_Fine_Sand": "65.3",
            "Percent_Med_Sand": "26",
            "Percent_Coarse_Sand": "0.6",
            "Percent_Tot_Sand": "91.9",
            "Percent_Clay": "6.9",
            "Percent_Silt": "1.2",
        }
        assert samples[2] == {
            "Study_Code": "WHONDRS_S19S",
            "Sample_ID": "S19S_0001_BULK-U",
            "Percent_Fine_Sand": "20.4",
            "Percent_Med_Sand": "68.6",
            "Percent_Coarse_Sand": "2.1",
            "Percent_Tot_Sand": "91.1",
            "Percent_Clay": "8.9",
            "Percent_Silt": "0",
        }


class TestIsAtLeastZeroWhenFloat:
    def test_it_detects_valid_strings(self):
        assert is_at_least_zero_when_float("0") is True
        assert is_at_least_zero_when_float("-0") is True
        assert is_at_least_zero_when_float("+0") is True  # leading + on zero
        assert is_at_least_zero_when_float("1") is True
        assert is_at_least_zero_when_float("+1") is True  # leading +
        assert is_at_least_zero_when_float("1.") is True  # trailing period
        assert is_at_least_zero_when_float("0.1") is True
        assert is_at_least_zero_when_float("1.1") is True
        assert is_at_least_zero_when_float("9999") is True
        assert is_at_least_zero_when_float("1e23") is True  # scientific notation
        assert is_at_least_zero_when_float("1E23") is True
        assert is_at_least_zero_when_float("1_000") is True  # _ for grouping (PEP 515)
        assert is_at_least_zero_when_float("1_3_5_7") is True  # major seven chord
        assert is_at_least_zero_when_float(" 1 ") is True  # surrounding whitespace

    def test_it_detects_invalid_strings(self):
        assert is_at_least_zero_when_float("-1") is False
        assert is_at_least_zero_when_float("-0.1") is False
        assert is_at_least_zero_when_float("-1.1") is False
        assert is_at_least_zero_when_float("-9999") is False
        assert is_at_least_zero_when_float("A") is False  # hex
        assert is_at_least_zero_when_float("0xA") is False  # hex with 0x prefix
        assert is_at_least_zero_when_float("") is False
        assert is_at_least_zero_when_float(" ") is False
        assert is_at_least_zero_when_float("1 2") is False  # mid-string whitespace
        assert is_at_least_zero_when_float("1+1") is False  # operation
        assert is_at_least_zero_when_float("1,000") is False  # comma
        assert is_at_least_zero_when_float("_1000") is False  # leading _
        assert is_at_least_zero_when_float("1000_") is False  # trailing _
        assert is_at_least_zero_when_float("1__000") is False  # double _
        assert is_at_least_zero_when_float("(1)") is False


class TestStoreSamplesInDatabase:
    def test_it_stores_samples_in_database(
        self, db_client: pymongo.MongoClient, example_samples: List[dict]
    ):
        result = store_samples_in_database(example_samples)

        # Examine the return value.
        assert len(result.inserted_ids) == len(example_samples)

        # Verify each of the example samples is in the collection.
        db = db_client[env["MONGO_DATABASE_NAME"]]
        collection = db[env["MONGO_COLLECTION_NAME"]]
        assert collection.count_documents({}) == len(example_samples)
        for ex_sample in example_samples:
            db_sample = collection.find_one({"Sample_ID": ex_sample["Sample_ID"]})
            assert ex_sample == db_sample

    def test_it_aborts_when_encountering_existing_sample_id_study_code_pair(
        self, db_client: pymongo.MongoClient, example_samples: List[dict]
    ):
        # Modify the example samples list so both the `Study_Code` and `Sample_ID` values
        # match between the first two samples. Note: the `Study_Code` already does match.
        example_samples[1]["Sample_ID"] = example_samples[0]["Sample_ID"]

        # Expect the function-under-test to raise an exception.
        with pytest.raises(pymongo.errors.BulkWriteError):
            store_samples_in_database(example_samples)

        # Verify only the first example sample is in the collection.
        db = db_client[env["MONGO_DATABASE_NAME"]]
        collection = db[env["MONGO_COLLECTION_NAME"]]
        assert collection.count_documents({}) == 1  # not 2 or 3
        ex_sample = example_samples[0]
        db_sample = collection.find_one({"Sample_ID": ex_sample["Sample_ID"]})
        assert ex_sample == db_sample