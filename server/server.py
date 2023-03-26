from os import environ as env
from typing import Annotated
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Path
from fastapi.responses import RedirectResponse
from fastapi.openapi.utils import get_openapi
from pymongo import MongoClient

app = FastAPI()

# Load variables defined in the `.env` file, into the `os.environ` dictionary.
# Note: Existing environment variables get priority; i.e. won't be overridden.
# Reference: https://github.com/theskumar/python-dotenv#getting-started
load_dotenv(verbose=True)


@app.get("/", include_in_schema=False)
def redirect_to_docs():
    """Redirects the client to the API documentation."""
    return RedirectResponse("/docs")


@app.get("/sampleid/{sample_id}", include_in_schema=False)
def redirect_to_samples(sample_id: str):
    """Redirects the client to the "samples" endpoint."""
    return RedirectResponse(f"/samples/{sample_id}")


@app.get(
    "/samples/{sample_id}",
    # Note: The kwargs below influence the OpenAPI schema/Swagger UI.
    tags=["samples"],
    summary="Get a sample",
    response_description="The sample having the specified `Sample_ID`",
)
def get_sample(
    # Note: The `description` kwarg influences the OpenAPI schema/Swagger UI.
    sample_id: Annotated[
        str, Path(description="The `Sample_ID` of the sample you want to get")
    ]
) -> dict:
    """Gets the sample having the specified `Sample_ID`."""

    # Fetch the specified sample from the MongoDB database.
    # Reference: https://pymongo.readthedocs.io/en/stable/tutorial.html#getting-a-single-document-with-find-one
    mongo_client: MongoClient = MongoClient(
        username=env["MONGO_USERNAME"],
        password=env["MONGO_PASSWORD"],
        host=env["MONGO_HOST"],
        port=int(env["MONGO_PORT"]),
    )
    db = mongo_client[env["MONGO_DATABASE_NAME"]]
    collection = db[env["MONGO_COLLECTION_NAME"]]
    sample_mapping = collection.find_one({"Sample_ID": sample_id})
    if sample_mapping is not None:
        # Return a version of the result that does not contain the `_id` item,
        # since (a) that item is not serializable to JSON (it's an `ObjectId`), and
        #       (b) it is not shown in the "requirements" document.
        #
        # Note: Since `find_one` returns a `Mapping` (not a `dict`) and PyCharm says
        #       I cannot use `del` on a `Mapping`, I first convert the `Mapping`
        #       into a `dict`; then, I use `del` on the `dict` and return the result.
        #
        sample = dict(sample_mapping)
        del sample["_id"]
        return sample
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to find a sample having Sample_ID: '{sample_id}'",
        )


def get_custom_openapi_schema():
    """
    Returns a custom OpenAPI schema.
    Reference: https://fastapi.tiangolo.com/advanced/extending-openapi/#generate-the-openapi-schema
    """
    # If the app lacks a "cached" schema, create and cache one.
    if not app.openapi_schema:
        openapi_schema = get_openapi(
            title="sediment-api",
            version="0.1.0",
            description="Sediment API",
            routes=app.routes,
        )
        # Effectively "cache" the schema for future reference.
        app.openapi_schema = openapi_schema
    return app.openapi_schema


# Override the default OpenAPI schema with a custom one.
#
# Note: I use `setattr` to resolve a "method-assign" error that mypy reported when
#       I was using the `app.openapi = fn` statement shown in the FastAPI docs.
#       Reference: https://github.com/python/mypy/issues/2427#issuecomment-480263443
#
setattr(app, "openapi", get_custom_openapi_schema)
