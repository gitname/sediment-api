FROM python:3.10-slim
WORKDIR /code

# Install the dependencies listed in the requirements.txt file.
#
# Note: `--no-cache-dir` tells pip to not save downloaded packages locally for future installation.
#       `--upgrade` tells pip to upgrade the packages if they are already installed.
#       Reference: https://fastapi.tiangolo.com/deployment/docker/#dockerfile
#
# Note: Here, I copy only the `requirements.txt` file; i.e. not files that change more frequently.
#
COPY ./requirements.txt /code/requirements.txt
RUN pip install \
    --no-cache-dir \
    --upgrade \
    -r /code/requirements.txt

# Copy all files, regardless of how frequently they get updated.
COPY . /code

# Serve the app.
#
# Note: The `--reload --reload-dir /code/server` tells uvicorn I want it to reload the app whenever
#       any Python file in the `/code/server` folder changes (I find this useful during development).
#       Reference: https://www.uvicorn.org/settings/#development
#
CMD ["uvicorn", "server.server:app", \
        "--host", "0.0.0.0", \
        "--port", "80", \
        "--reload", \
        "--reload-dir", "/code/server"]
