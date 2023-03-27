# Sediment API

> Hello! I wrote the code in this repository as an exercise. The exercise prompt was, in summary, to (a) write a Python
> script someone could use to extract data from a CSV file and store that data in a MongoDB database; and (b) create an
> HTTP API that accepts requests for a single item (identified by its `Sample_ID`) and returns that item in JSON format.

## Table of contents

<!-- TOC -->
* [Sediment API](#sediment-api)
  * [Table of contents](#table-of-contents)
  * [Overview](#overview)
  * [Usage](#usage)
    * [Exercise-specific](#exercise-specific)
    * [General](#general)
  * [Development](#development)
    * [Environment](#environment)
    * [Testing](#testing)
    * [Static type checking](#static-type-checking)
    * [Code formatting](#code-formatting)
    * [Dependencies](#dependencies)
  * [Roadmap](#roadmap)
<!-- TOC -->

## Overview

This repository contains Python scripts people can use to extract data from a CSV file,
store that data in a MongoDB database,
and provide access to that data via an HTTP API.

The scripts are:

1. `parser/parser.py`: A file parser people can use to extract data from a CSV file and insert it into a database
2. `server/server.py`: A web server people can use to access that data via an HTTP API

Here's a diagram showing how data flows into, between, and out of those scripts.

```mermaid
%% This is a flowchart written using Mermaid syntax.
%% GitHub will render it as an image.
%%
%% References: 
%% - https://mermaid.js.org/syntax/flowchart.html
%% - https://github.blog/2022-02-14-include-diagrams-markdown-files-mermaid/

flowchart LR
    parser[[parser.py]]
    db[(Database)]
    file[CSV File]
    client[HTTP Client]
    server[[server.py]]

    parser --> db
    db --> server

    subgraph File Parser
        parser
    end

    file -. CSV .-> parser

    subgraph Web Server
        server
    end

    server -. JSON .-> client
```

## Usage

### Exercise-specific

Here's how you can produce the behavior described in the exercise prompt.

1. Install [Docker](https://www.docker.com/) onto your computer.
2. Clone (or download and extract) this repository onto your computer.
3. Open a console in the root folder of the repository.
4. Copy the example config file and name the copy "`.env`".
   ```shell
   cp .env.example .env
   ```
5. Start the web server and MongoDB (in Docker containers).
   ```shell
   docker-compose up
   ```
   > **Note:** That command will run the containers in the foreground, taking over your console. You can open a new
   > console to issue the remaining commands.
6. Run the parser (in the `app` container).
   ```shell
   docker exec -it app python parser/parser.py parser/example_data/WHONDRS_S19S_Sediment_GrainSize.csv
   ```
7. In a web browser, visit http://localhost:8000/samples/S19S_0001_BULK-D
   - The web browser will show a sample in JSON format.

### General

Here's how you can use the system in general.

1. Do steps 1-5 shown in the "Exercise-specific" section above.
2. (Optional) Put a custom CSV file you want to parse, anywhere within the repository's file tree 
   (e.g. at `parser/example_data/samples.csv`.
   > **Note:** All files within the repository's file tree are accessible from within the `app` container,
   > per the `volumes` mapping defined in `docker-compose.yml`.
3. Run the parser, specifying the path to the CSV file you want to parse.
   ```shell
   # Specify the path as a relative path based upon the repository root (e.g. parser/example_data/samples.csv).
   docker exec -it app python parser/parser.py <path_to_csv_file>
   ```
4. Submit an HTTP GET request to a URL having the format: `http://localhost:8000/samples/<Sample_ID>`
5. (Optional) Visit the **interactive API documentation** at http://localhost:8000/docs

You can also **run tests**, **perform static type checking**, and **format the code**.
Instructions for doing those things are in the "Development" section below.

## Development

> **Note:** Unless otherwise specified, all commands shown in this section are written under the assumption you are in
> the root folder of the repository.

### Environment

This repository contains a Docker-based development environment.

You can configure the development environment by copying the `./.env.example` file and naming it `.env`; like this:

```shell
cp .env.example .env
```

> **Note:** The values in `env.example` (and, now, `.env`) are already sufficient for the development environment.

You can instantiate the development environment by issuing the following command:

```shell
docker-compose up

# Or, if you've made changes to the Dockerfile or `requirements.txt`:
docker-compose up --build
```

> **Note:** That will cause Docker to instantiate a container for each service described in `docker-compose.yml`.

With the development environment up and running, you can access a `bash` shell running on the `app` container
(i.e. the container that has Python and all the script dependencies installed) by issuing the following command:

```shell
docker exec -it app bash
```

### Testing

The tests in this repository were written using [pytest](https://docs.pytest.org/), a Python test framework and test
runner.

With the development environment up and running, you can **run all the tests** in the repository by issuing the
following command:

```shell
# From the `app` container:
pytest -v

# Or, from the Docker host:
docker exec -it app pytest -v
```

### Static type checking

You can use [mypy](https://mypy.readthedocs.io/en/latest/) to perform static type checking on the Python code in this
repository.

With the development environment up and running, you can **perform static type checking** by issuing the following
command:

```shell
# From the `app` container:
mypy

# Or, from the Docker host:
docker exec -it app mypy
```

> Note: When you run `mypy` as shown above, it will run according to the configuration specified in `mypy.ini`.

### Code formatting

The code in this project is formatted using [Black](https://black.readthedocs.io/en/stable/), which is
an "[opinionated](https://black.readthedocs.io/en/stable/the_black_code_style/index.html)"—but still PEP 8-compliant—code
formatter.

With the development environment up and running, you can **format all the Python code** in the repository by issuing the
following command:

```shell
# From the `app` container:
black .

# Or, from the Docker host:
docker exec -it app black .
```

### Dependencies

I wrote the Python scripts in this repository using Python version `3.10.10`.

The `requirements.txt` file contains a list of all the dependencies of the Python scripts in this repository.
I generated (and updated) the file by issuing the following command:

```shell
# From the `app` container:
pip freeze > requirements.txt

# Or, from the Docker host:
docker exec -it app pip freeze > requirements.txt
```

The table below contains the names of all the packages I explicitly installed via `pip install <name>` while writing the Python scripts in this repository:

| Name                | Description                | I use it to...                  | References                                                     |
|---------------------|----------------------------|---------------------------------|----------------------------------------------------------------|
| `black`             | Code formatter             | Format Python code              | [Documentation](https://black.readthedocs.io/en/stable)        |
| `fastapi`           | HTTP API framework         | Process HTTP requests           | [Documentation](https://fastapi.tiangolo.com/)                 |
| `httpx`             | HTTP client                | Submit HTTP requests (in tests) | [Documentation](https://www.python-httpx.org/)                 |
| `mypy`              | Static type checker        | Verify data type consistency    | [Documentation](https://mypy.readthedocs.io/en/latest/)        |
| `pymongo`           | Synchronous MongoDB driver | Interact with the database      | [Documentation](https://www.mongodb.com/docs/drivers/pymongo/) |
| `pytest`            | Test framework             | Run the tests                   | [Documentation](https://docs.pytest.org/en/7.2.x/)             |
| `python-dotenv`     | Configuration loader       | Read the `.env` file            | [Documentation](https://pypi.org/project/python-dotenv/)       |
| `typer[all]`        | CLI framework              | Process CLI input and output    | [Documentation](https://typer.tiangolo.com/)                   |
| `uvicorn[standard]` | ASGI web server            | Serve the FastAPI app           | [Documentation](https://www.uvicorn.org/)                      |

> **Note:** Packages listed in `requirements.txt` that are not listed above, are packages that were automatically
> installed by `pip` when I installed the packages listed above. In other words, they are "dependencies of
> dependencies" (i.e. dependencies of the packages listed above).

## Roadmap

Here are some things I am considering doing for this project.

1. Create a Pydantic model for the "sample" object and use it to
   (a) [validate and sanitize](https://docs.pydantic.dev/usage/validators/) the data extracted from the CSV file
   (i.e. `"-9999" → None`); (b) display the API response's
   [JSON schema](https://fastapi.tiangolo.com/tutorial/response-model/#see-it-in-the-docs) in the API docs and
   (c) automatically  [filter out](https://fastapi.tiangolo.com/tutorial/response-model/#fastapi-data-filtering)
   the `_id` field from the API response. Item (a) would happen in `parser.py` and items (b) and (c) would happen
   in `server.py`.
2. Update the parser to strip leading/trailing whitespace from the values extracted from the CSV file.
3. Update the parser so the call to `insert_many` is wrapped within a `try/except`. Currently, trying to insert a sample
   whose `Study_Code` and `Sample_ID` (together) match those of an existing sample, crashes the parser (since the
   `pymongo.errors.BulkWriteError` exception is not being caught). That exception is raised because the MongoDB
   collection has a "unique" index consisting of those two fields.
