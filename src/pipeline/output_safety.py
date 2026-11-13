"""Create new result files without truncating inputs, aliases or previous results."""
from contextlib import ExitStack
import os
from pathlib import Path

from src.pipeline.input_validation import InputValidationError


def write_new_outputs(results, sources=()):
    """Reserve every output exclusively before writing any content.

    Text uses LF internally and native newline translation on disk. Existing
    files (including hard links and dangling symlinks) are never overwritten.
    This is not a crash-atomic multi-file transaction or a hostile-directory
    sandbox; callers must control their input and output directories.
    """
    results = [(Path(path).absolute(), text) for path, text in results]
    sources = [Path(path) for path in sources]
    checked = list(sources)
    for path, _ in results:
        for other in checked:
            if path.resolve() == other.resolve() or (
                path.exists() and other.exists() and path.samefile(other)
            ):
                raise InputValidationError("輸出不能與輸入或另一個輸出指向同一檔案（含硬連結）。")
        checked.append(path)
    # Check the entire set before creating even the first placeholder.
    for path, _ in results:
        if os.path.lexists(path):
            raise InputValidationError(f"輸出已存在，拒絕覆寫；請使用新的結果路徑：{path}")

    created = []
    try:
        with ExitStack() as stack:
            streams = []
            for path, text in results:
                path.parent.mkdir(parents=True, exist_ok=True)
                # 'x' performs exclusive creation in the open itself. Retain
                # this handle; never reopen the pathname with truncating 'w'.
                stream = stack.enter_context(path.open("x", encoding="utf-8"))
                created.append((path, os.fstat(stream.fileno())))
                streams.append((stream, text))
            for stream, text in streams:
                stream.write(text)
    except BaseException:
        # Only remove files created by this call, and only if their identity
        # still matches. In particular, do not remove a competing creator's file.
        for path, identity in reversed(created):
            try:
                if os.path.samestat(path.lstat(), identity):
                    path.unlink()
            except OSError:
                pass
        raise
