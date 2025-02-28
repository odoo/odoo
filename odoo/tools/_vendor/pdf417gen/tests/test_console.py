from mock import patch
from pdf417gen import console


def test_print_usage(capsys):
    console.print_usage()
    out, err = capsys.readouterr()
    assert "Usage: pdf417gen [command]" in out
    assert not err


def test_print_err(capsys):
    console.print_err("foo")
    out, err = capsys.readouterr()
    assert not out
    assert "foo" in err


@patch('pdf417gen.console.encode', return_value="RETVAL")
@patch('pdf417gen.console.render_image')
def test_encode(render_image, encode, capsys):
    text = "foo"

    console.do_encode([text])

    encode.assert_called_once_with(
        text,
        columns=6,
        encoding='utf-8',
        security_level=2
    )

    render_image.assert_called_once_with(
        'RETVAL',
        bg_color='#FFFFFF',
        fg_color='#000000',
        padding=20,
        ratio=3,
        scale=3
    )


@patch('sys.stdin.read', return_value="")
@patch('pdf417gen.console.encode', return_value="RETVAL")
@patch('pdf417gen.console.render_image')
def test_encode_no_input(render_image, encode, read, capsys):
    console.do_encode([])

    encode.assert_not_called()
    render_image.assert_not_called()
    read.assert_called_once_with()

    out, err = capsys.readouterr()
    assert not out
    assert "No input given" in err


@patch('pdf417gen.console.encode', return_value="RETVAL")
@patch('pdf417gen.console.render_image')
def test_encode_exception(render_image, encode, capsys):
    encode.side_effect = ValueError("FAILED")

    console.do_encode(["foo"])

    encode.assert_called_once_with(
        "foo",
        columns=6,
        encoding='utf-8',
        security_level=2
    )
    render_image.assert_not_called()

    out, err = capsys.readouterr()
    assert not out
    assert "FAILED" in err
