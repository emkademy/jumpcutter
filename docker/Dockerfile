FROM python:3.11-slim

ARG USER_ID=1000
ARG DEVELOPMENT=0
ARG USER_NAME=emkademy

ENV HOME="/home/${USER_NAME}"
ENV LC_ALL C.UTF-8
ENV \
    PYTHONUNBUFFERED=1 \
    PIPENV_RELEASE=2020.11.15 \
    PIPENV_NOSPIN=1 \
    PIPENV_TIMEOUT=900 \
    VIRTUAL_ENV="${HOME}/venv" \
    PATH="${HOME}/venv/bin:${PATH}" \
    PYTHONPATH="/app:${PYTHONPATH}" \ 
    BUILD_POETRY_LOCK="${HOME}/poetry.lock.build"

RUN apt-get -qq update && apt-get -qq -y install curl vim

RUN addgroup --system --gid "${USER_ID}" "${USER_NAME}" \
    && adduser --system --home "${HOME}" --uid "${USER_ID}" \
    --ingroup "${USER_NAME}" "${USER_NAME}"

RUN mkdir -p /app/jumpcutter && chown -R "${USER_NAME}" /app

USER "${USER_NAME}"

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="${PATH}:${HOME}/.poetry/bin"

COPY . /app
WORKDIR /app

RUN python3 -m venv $VIRTUAL_ENV \
    && if [ $DEVELOPMENT -eq 1 ]; then \
        poetry install; \
        cp -f poetry.lock $BUILD_POETRY_LOCK; \
    else \
        [ -f poetry.lock ] || { echo 'No poetry.lock found' ; exit 1; }; \
        poetry install --no-dev; \
    fi \
    && rm -rf $HOME/.cache/*

CMD ["/bin/sh"]

