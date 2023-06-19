# Introduction

Kilonova is a Python 3 script designed to automate the task of backing up, restoring and cloning Docker & Podman volumes.

# Installation

The entire script is a single Python file at the root of this repository. The following example shows one possible method of installing the script:

```sh
wget https://raw.githubusercontent.com/apsoyka/kilonova/main/kilonova.py
chmod +x kilonova.py
mv kilonova.py /usr/bin/kilonova
```

# Usage

Kilonova has a simple Command-Line Interface (CLI). If you are ever unsure how to use the script, simply call `kilonova --help` for guidance.

## Backup

This command will backup the contents of `volume` into the file `volume.tar.gz`.

```sh
kilonova backup volume volume.tar.gz
```

## Restore

This command will restore the contents of `volume.tar.gz` into `volume`.

```sh
kilonova restore volume.tar.gz volume
```

## Clone

This command will cause the contents of `volume1` to be copied into `volume2`.

```sh
kilonova clone volume1 volume2
```
