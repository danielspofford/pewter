import pytest

import puter.log as log


def test_text(mocker):
    mock_echo = mocker.patch("click.echo")
    log.text("text")
    mock_echo.assert_called_with("text")

def test_data_dir(mocker):
    mock_echo = mocker.patch("click.echo")
    log.text("text")
    mock_echo.assert_called_with("text")

def test_commit(mocker):
    mock_isoformat = mocker.patch("datetime.now.isoformat")
    mock_data_dir = mocker.patch("puter.data_dir")
    mock_data_dir = mocker.patch("puter.data_dir")
    log.text("text")
    mock_click.assert_called_with("text")
