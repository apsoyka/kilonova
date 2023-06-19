#!/usr/bin/env python3

import sys
import tempfile
import argparse
import subprocess
import pathlib
import shutil
import logging

IMAGE = "docker.io/library/busybox:1.36.0"

def engine_installed(engine):
    return shutil.which(engine) is not None

def volume_exists(engine, volume):
    if engine == "docker":
        command = [
            "docker",
            "volume",
            "ls",
            "-f",
            f"name={volume}"
        ]

        result = subprocess.run(command, capture_output = True, text = True)

        # Get only the volume name column lines
        lines = [column.split()[1] for column in result.stdout.splitlines()]

        return volume in lines
    else:
        command = [
            "podman",
            "volume",
            "exists",
            volume
        ]

        result = subprocess.run(command)

        return result.returncode == 0

def backup(arguments):
    """
        Backup a volume.
    """

    engine = arguments.engine
    volume = arguments.volume
    output = arguments.output

    if not volume_exists(engine, volume):
        logging.error("Cannot backup data from a volume that does not exist")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as directory:
        filename = f"{volume}.tar.gz"
        command = [
            engine,
            "run",
            "--rm",
            "-it",
            "-v",
            f"{volume}:/in:z",
            "-v",
            f"{directory}:/out:z",
            IMAGE,
            "sh",
            "-c",
            f"'cd /in && tar vacf /out/{filename} .'"
        ]
        shell = " ".join(command)

        result = subprocess.run(shell, shell = True)

        if result.returncode != 0:
            logging.error("Failed to backup a volume")
            sys.exit(1)

        source = pathlib.Path(directory, filename).resolve()
        target = pathlib.Path(output).resolve()

        # Move the temporary file to the user-specified location.
        shutil.move(source, target)

        logging.debug(f"{source} -> {target}")
        logging.info(f"Finished backing up {volume} to {filename}")

def restore(arguments):
    """
        Restore a volume from a backup.
    """

    engine = arguments.engine
    input = arguments.input
    volume = arguments.volume

    if not volume_exists(engine, volume):
        logging.error("Cannot restore data to a volume that does not exist")
        sys.exit(1)

    path = pathlib.Path(input).resolve()

    if not path.exists():
        logging.error(f"The file at {path} does not exist")
        sys.exit(1)

    filename = path.name
    command = [
            engine,
            "run",
            "--rm",
            "-it",
            "-v",
            f"{path}:/in/{filename}:z",
            "-v",
            f"{volume}:/out:z",
            IMAGE,
            "sh",
            "-c",
            f"'cd /out && tar vxf /in/{filename}'"
    ]
    shell = " ".join(command)

    result = subprocess.run(shell, shell = True)

    if result.returncode != 0:
        logging.error("Failed to restore a volume")
        sys.exit(1)

    logging.info(f"Finished restoring {volume} from {filename}")

def clone(arguments):
    """
        Create an exact copy of a volume.
    """

    engine = arguments.engine
    source = arguments.source
    target = arguments.target

    if not volume_exists(engine, source):
        logging.error("The source volume does not exist")
        sys.exit(1)

    if not volume_exists(engine, target):
        logging.error("The target volume does not exist")
        sys.exit(1)

    command = [
            engine,
            "run",
            "--rm",
            "-it",
            "-v",
            f"{source}:/in/:z",
            "-v",
            f"{target}:/out:z",
            IMAGE,
            "sh",
            "-c",
            "'cp -rfv /in/* /out'"
    ]
    shell = " ".join(command)

    result = subprocess.run(shell, shell = True)

    if result.returncode != 0:
        logging.error("Failed to clone a volume")
        sys.exit(1)

    logging.info(f"Finished cloning from {source} to {target}")

def main():
    parser = argparse.ArgumentParser("Kilonova")

    parser.add_argument(
        "-e",
        "--engine",
        choices = ["docker", "podman"],
        default = "docker",
        help = "choose which container engine to use"
    )

    group_verbosity = parser.add_mutually_exclusive_group()

    group_verbosity.add_argument(
        "-v",
        "--verbose",
        action = "store_true",
        help = "verbose mode"
    )
    group_verbosity.add_argument(
        "-q",
        "--quiet",
        action = "store_true",
        help = "quiet mode"
    )

    subparsers = parser.add_subparsers(required = True)

    parser_backup = subparsers.add_parser("backup")
    parser_backup.add_argument("volume", help = "the volume to backup")
    parser_backup.add_argument("output", help = "where to store the resulting backup file")
    parser_backup.set_defaults(func = backup)

    parser_restore = subparsers.add_parser("restore")
    parser_restore.add_argument("input", help = "a file containing backup data")
    parser_restore.add_argument("volume", help = "the volume to place data into")
    parser_restore.set_defaults(func = restore)

    parser_clone = subparsers.add_parser("clone")
    parser_restore.add_argument("source", help = "the volume containing data to be transfered")
    parser_restore.add_argument("target", help = "the volume to transfer data into")
    parser_clone.set_defaults(func = clone)

    arguments = parser.parse_args()

    level = logging.INFO

    if arguments.verbose:
        level = logging.DEBUG

    if arguments.quiet:
        level = logging.WARN

    logging.basicConfig(format = "%(levelname)s %(message)s", level = level)

    engine = arguments.engine

    if not engine_installed(engine):
        logging.error(f"The {engine} container engine is not installed")
        sys.exit(1)

    arguments.func(arguments)

if __name__ == "__main__":
    main()
