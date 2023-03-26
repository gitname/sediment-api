from os import environ as env
from typing import Iterator
from fastapi.testclient import TestClient  # `TestClient` inherits from `httpx.Client`
from pymongo import MongoClient, ASCENDING
from pymongo.database import Database
import pytest
from .server import app

# Reference: https://fastapi.tiangolo.com/tutorial/testing/
client = TestClient(app)


@pytest.fixture(autouse=True)  # automatically "used" by each test
def seeded_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[Database]:
    """
    Patches the database name environment variable to refer to a test database.
    Seeds the test database.
    Yields a handle to the seeded test database.
    Deletes the test database after the dependent test ends.
    """
    # Patch a specific environment variable so both the test and the app-under-test use a temporary database.
    # Reference: https://docs.pytest.org/en/stable/how-to/monkeypatch.html#monkeypatching-environment-variables
    db_name = "_test"
    monkeypatch.setenv("MONGO_DATABASE_NAME", db_name)

    # Seed the database.
    mongo_client: MongoClient = MongoClient(
        username=env["MONGO_USERNAME"],
        password=env["MONGO_PASSWORD"],
        host=env["MONGO_HOST"],
        port=int(env["MONGO_PORT"]),
    )
    db = mongo_client[db_name]
    collection = db[env["MONGO_COLLECTION_NAME"]]
    collection.create_index([("Sample_ID", ASCENDING)])
    collection.create_index(
        [("Sample_ID", ASCENDING), ("Study_Code", ASCENDING)], unique=True
    )
    collection.insert_many(
        [
            {
                "Study_Code": "some_study_code",
                "Sample_ID": "sample_a",
                "C": "11",
                "D": "2.2",
            },
            {
                "Study_Code": "some_study_code",
                "Sample_ID": "sample_b",
                "C": "22",
                "D": "3.3",
            },
            {
                "Study_Code": "some_study_code",
                "Sample_ID": "sample_c",
                "C": "33",
                "D": "4.4",
            },
        ]
    )

    yield db

    # Delete the database.
    mongo_client.drop_database(db_name)


class TestGetRoot:
    def test_it_redirects_to_docs_route(self):
        res = client.get("/", follow_redirects=False)
        assert res.status_code == 307
        assert res.headers["location"] == "/docs"


class TestGetSampleID:
    def test_it_redirects_to_samples_route(self):
        res = client.get("/sampleid/some_sample_id", follow_redirects=False)
        assert res.status_code == 307
        assert res.headers["location"] == "/samples/some_sample_id"


class TestGetSamples:
    def test_it_responds_with_the_specified_sample(self):
        res = client.get("/samples/sample_b")
        assert res.status_code == 200
        json = res.json()
        assert json["Study_Code"] == "some_study_code"
        assert json["Sample_ID"] == "sample_b"
        assert json["C"] == "22"
        assert json["D"] == "3.3"

    def test_it_responds_with_404_error_when_sample_is_not_found(self):
        res = client.get("/samples/sample_d")
        assert res.status_code == 404
