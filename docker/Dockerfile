FROM debian:trixie-slim

LABEL maintainer="4950815+RicardoJeronimo@users.noreply.github.com" \
      org.opencontainers.image.title="Patchman" \
      org.opencontainers.image.base.name="debian:trixie-slim" \
      org.opencontainers.image.source="https://github.com/RicardoJeronimo/patchman"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATCHMAN_HOME=/srv/patchman

RUN apt-get -y update && apt-get -y upgrade && \
    apt-get install -y --no-install-recommends apache2 git libapache2-mod-wsgi-py3 libmagic1 mariadb-client python3-debian python3-defusedxml python3-lxml python3-mysqldb python3-pip python3-psycopg2 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR ${PATCHMAN_HOME}

COPY requirements.txt .

RUN pip install --no-cache-dir --break-system-packages setuptools -r requirements.txt

RUN groupadd --system patchman && \
    useradd --system --gid patchman --no-create-home patchman && \
    mkdir -p /var/lib/patchman/db && \
    chown patchman:www-data /var/lib/patchman/db && \
    chmod 2770 /var/lib/patchman/db

COPY . ${PATCHMAN_HOME}/
COPY ./etc/patchman/apache.conf.example /etc/apache2/sites-available/patchman.conf

RUN ${PATCHMAN_HOME}/setup.py install --no-compile && \
    rm -rf build/ dist/ *.egg-info/ .eggs/ /root/.cache/

RUN a2enmod wsgi && \
    a2ensite patchman && \
    a2dissite 000-default

COPY ./docker/docker-entrypoint.sh docker-entrypoint.sh

EXPOSE 80

ENTRYPOINT ["./docker-entrypoint.sh"]
