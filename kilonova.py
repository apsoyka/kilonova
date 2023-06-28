#!/usr/bin/env python3

import sys
import tempfile
import argparse
import subprocess
import pathlib
import shutil
import logging

IMAGE = "docker.io/library/busybox:1.36.0"

def volume_empty(engine, volume):
    """
        Check whether a volume is empty.
    """
    directory = "/volume"

    command = [
        engine,
        "run",
        "--rm",
        "-it",
        "--mount",
        f"type=volume,source={volume},target={directory}",
        IMAGE,
        "ls",
        "-A",
        directory
    ]

    shell = " ".join(command)

    logging.debug(shell)

    result = subprocess.run(shell, shell = True, capture_output = True, text = True)

    if result.returncode != 0:
        logging.error(f"Failed to check if volume is empty: {result.stderr or result.stdout}")
        sys.exit(1)

    return result.stdout == ""

def engine_installed(engine):
    """
        Check whether the specified engine is installed.
    """
    return shutil.which(engine) is not None

def volume_exists(engine, volume):
    """
        Check whether a volume exists.
    """
    if engine == "docker":
        command = [
            "docker",
            "volume",
            "ls"
        ]

        shell = " ".join(command)

        logging.debug(shell)

        result = subprocess.run(shell, shell = True, capture_output = True, text = True)
        output = result.stdout

        if result.returncode != 0:
            logging.error(f"Failed to check for volume existence: {output}")
            exit(1)

        # Get only the volume name column lines
        lines = [column.split()[1] for column in output.splitlines()]

        return volume in lines
    else:
        command = [
            "podman",
            "volume",
            "exists",
            volume
        ]

        shell = " ".join(command)

        logging.debug(shell)

        result = subprocess.run(shell, shell = True)
        output = result.stdout

        if result.returncode == 0:
            return True
        elif output != "":
            return False
        else:
            logging.error(f"Failed to check for volume existence: {output}")
            exit(1)

def backup(arguments):
    """
        Backup a volume.
    """

    engine = arguments.engine
    volume = arguments.volume
    output = arguments.output
    quiet = arguments.quiet
    options = "acf" if quiet else "vacf"
    source_directory = "/in"
    target_directory = "/out"
    target = pathlib.Path(output).resolve()
    filename = target.name

    if not volume_exists(engine, volume):
        logging.error("Cannot backup data from a volume that does not exist")
        sys.exit(1)

    if volume_empty(engine, volume):
        logging.error("Cannot backup data from an empty volume")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as temp_directory:
        command = [
            engine,
            "run",
            "--rm",
            "-it",
            "--mount",
            f"type=volume,source={volume},target={source_directory}",
            "--mount",
            f"type=bind,source={temp_directory},target={target_directory}",
            IMAGE,
            "tar",
            options,
            f"{target_directory}/{filename}",
            "-C",
            source_directory,
            "."
        ]

        shell = " ".join(command)

        logging.debug(shell)

        result = subprocess.run(shell, shell = True)

        if result.returncode != 0:
            logging.error("Failed to backup a volume")
            sys.exit(1)

        source = pathlib.Path(temp_directory, filename).resolve()

        # Move the temporary file to the user-specified location.
        shutil.move(source, target)

        logging.debug(f"{source} -> {target}")
        logging.info(f"Finished backing up {volume} to {target}")

def restore(arguments):
    """
        Restore a volume from a backup.
    """

    engine = arguments.engine
    input = arguments.input
    volume = arguments.volume
    quiet = arguments.quiet
    options = "xf" if quiet else "vxf"

    if not volume_exists(engine, volume):
        logging.error("Cannot restore data to a volume that does not exist")
        sys.exit(1)

    if not volume_empty(engine, volume):
        logging.error("Cannot restore data to a volume that is not empty")
        sys.exit(1)

    input_path = pathlib.Path(input).resolve()

    if not input_path.exists():
        logging.error(f"{input_path} does not exist")
        sys.exit(1)

    source = f"/in/{input_path.name}"
    target = "/out"

    command = [
            engine,
            "run",
            "--rm",
            "-it",
            "--mount",
            f"type=bind,source={input_path},target={source}",
            "--mount",
            f"type=volume,source={volume},target={target}",
            IMAGE,
            "tar",
            options,
            source,
            "-C",
            target
    ]

    shell = " ".join(command)

    logging.debug(shell)

    result = subprocess.run(shell, shell = True)

    if result.returncode != 0:
        logging.error(f"Failed to restore a volume")
        sys.exit(1)

    logging.info(f"Finished restoring {volume} from {input_path}")

def clone(arguments):
    """
        Create an exact copy of a volume.
    """

    engine = arguments.engine
    source = arguments.source
    target = arguments.target
    quiet = arguments.quiet
    options = "-rfp" if quiet else "-rfvp"
    source_directory = "/in"
    target_directory = "/out"

    if not volume_exists(engine, source):
        logging.error("The source volume does not exist")
        sys.exit(1)

    if volume_empty(engine, source):
        logging.error("The source volume can not be empty")
        sys.exit(1)

    if not volume_exists(engine, target):
        logging.error("The target volume does not exist")
        sys.exit(1)

    if not volume_empty(engine, target):
        logging.error("The target volume must be empty")
        sys.exit(1)

    command = [
            engine,
            "run",
            "--rm",
            "-it",
            "--mount",
            f"type=volume,source={source},target={source_directory}",
            "--mount",
            f"type=volume,source={target},target={target_directory}",
            IMAGE,
            "cp",
            options,
            f"{source_directory}/.",
            target_directory
    ]

    shell = " ".join(command)

    logging.debug(shell)

    result = subprocess.run(shell, shell = True)

    if result.returncode != 0:
        logging.error(f"Failed to clone a volume")
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
    parser_clone.add_argument("source", help = "the volume containing data to be transfered")
    parser_clone.add_argument("target", help = "the volume to transfer data into")
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
