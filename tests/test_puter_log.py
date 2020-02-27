import json
from pathlib import Path
from unittest.mock import mock_open

import pytest

import puter.log as log

from .conftest import TEST_DATA_DIR


def test_text(mocker):
    mock_echo = mocker.patch("click.echo")
    log.text("text")
    mock_echo.assert_called_with("text")


def test_data(mocker):

    # Had to patch datetime in this way because python objected to patching
    # "now" directly.
    mock_dt = mocker.patch("puter.log.datetime")
    mock_dt.now.return_value = mocker.MagicMock(isoformat=lambda: "fake time")

    m = mock_open()  # https://docs.python.org/3.7/library/unittest.mock.html#mock-open
    mocker.patch("puter.log.open", m)

    to_log = {"foo": "bar"}
    log.data(to_log)

    m.assert_called_once_with(Path(TEST_DATA_DIR) / "puter" / "log.txt", "a")

    written_file_contents = m().write.mock_calls[0][1][0]
    written_json = json.loads(written_file_contents)

    assert all(k in written_json for k in to_log.keys())
    assert all(k in written_json["meta"] for k in ["stack", "datetime"])
