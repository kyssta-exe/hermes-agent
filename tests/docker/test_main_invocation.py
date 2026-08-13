"""Harness: docker run <image> [cmd...] invocation patterns.

These tests MUST pass on the current tini-based image AND continue to
pass after the Phase 2 s6 migration. Any behavior drift is a regression.

The harness expects ``built_image`` and ``container_name`` fixtures from
``tests/docker/conftest.py``. When Docker isn't available every test
here is skipped at collection time.
"""
from __future__ import annotations

import subprocess


def test_no_args_starts_hermes(built_image: str) -> None:
    """``docker run <image>`` should start hermes cleanly.

    We invoke ``--version`` so the call exits without needing a configured
    model. Exit code may be 0 (printed version) or 1 (config bootstrapping
    failure on a fresh volume), but never a stack trace.
    """
    r = subprocess.run(
        ["docker", "run", "--rm", built_image, "--version"],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode in (0, 1), (
        f"Unexpected exit {r.returncode}: stderr={r.stderr!r}"
    )
    assert "Traceback" not in r.stderr


def test_chat_subcommand_passthrough(built_image: str) -> None:
    """``docker run <image> chat --help`` should exec ``hermes chat --help``.

    Uses ``--help`` so the call doesn't need an upstream model configured.
    """
    r = subprocess.run(
        ["docker", "run", "--rm", built_image, "chat", "--help"],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0
    combined = (r.stdout + r.stderr).lower()
    assert "chat" in combined or "usage" in combined




def test_bash_pattern(built_image: str) -> None:
    """``docker run <image> bash -c 'echo ok'`` should exec bash directly."""
    r = subprocess.run(
        ["docker", "run", "--rm", built_image, "bash", "-c", "echo ok"],
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0
    assert "ok" in r.stdout


def test_group_add_survives_main_wrapper_privilege_drop(
    built_image: str,
) -> None:
    """Docker-granted groups must survive ``s6-setuidgid hermes``.

    The command runs through the image's real s6 lifecycle and
    ``main-wrapper.sh``. Without the stage2 repair, ``s6-setuidgid`` calls
    ``initgroups()`` and silently drops GID 1001 because it has no matching
    membership in the image's ``/etc/group``.
    """
    r = subprocess.run(
        [
            "docker", "run", "--rm", "--group-add", "1001", built_image,
            "sh", "-c",
            "printf 'RUNTIME_UID='; id -u; printf 'RUNTIME_GROUPS='; id -G",
        ],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0, (
        f"docker run failed: stdout={r.stdout!r} stderr={r.stderr!r}"
    )
    runtime_uid_lines = [
        line for line in r.stdout.splitlines() if line.startswith("RUNTIME_UID=")
    ]
    runtime_group_lines = [
        line for line in r.stdout.splitlines() if line.startswith("RUNTIME_GROUPS=")
    ]
    assert runtime_uid_lines == ["RUNTIME_UID=10000"], (
        "The command reached through main-wrapper.sh did not run as hermes: "
        f"stdout={r.stdout!r}"
    )
    assert len(runtime_group_lines) == 1, (
        f"Expected one runtime group marker: stdout={r.stdout!r}"
    )
    runtime_groups = runtime_group_lines[0].removeprefix("RUNTIME_GROUPS=").split()
    assert "1001" in runtime_groups, (
        "GID 1001 was lost between Docker PID 1 and the command reached "
        f"through main-wrapper.sh: groups={runtime_groups!r}, "
        f"stdout={r.stdout!r}"
    )


def test_container_exit_code_matches_inner_exit(built_image: str) -> None:
    """The container exit code must match the inner process's exit code.

    Critical for CI: ``docker run <image> hermes batch ...`` returns a
    non-zero status when batch fails. Phase 2 (s6) must preserve this.
    """
    r = subprocess.run(
        ["docker", "run", "--rm", built_image, "sh", "-c", "exit 42"],
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 42
