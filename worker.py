"""Sage-only worker. Its stdout/stderr never carry MCP or result JSON."""
import ast
import json
from pathlib import Path
import sys
import traceback

MAX_TEXT = 20_000


def limited(value):
    text = str(value)
    return text[:MAX_TEXT], len(text) > MAX_TEXT


def main():
    request_path, result_path = map(Path, sys.argv[1:3])
    try:
        import sage.all as sage
        from sage.repl.preparse import preparse_file

        request = json.loads(request_path.read_text())
        namespace = {key: getattr(sage, key) for key in dir(sage) if not key.startswith("_")}
        namespace.update(__name__="__main__", x=sage.SR.var("x"))
        tree = ast.parse(preparse_file(request["code"]), filename="<sage>", mode="exec")
        last = tree.body.pop() if tree.body and isinstance(tree.body[-1], ast.Expr) else None
        exec(compile(tree, "<sage>", "exec"), namespace)
        value = eval(compile(ast.Expression(last.value), "<sage>", "eval"), namespace) if last else None
        rendered, truncated = limited(value) if value is not None else (None, False)
        result = {
            "ok": True, "result": rendered, "result_truncated": truncated,
            "type": type(value).__module__ + "." + type(value).__qualname__ if value is not None else None,
        }
        if request["include_latex"] and value is not None:
            try:
                result["latex"], result["latex_truncated"] = limited(sage.latex(value))
            except Exception as exc:
                result["latex"] = None
                result["latex_error"] = limited(exc)[0]
    except BaseException as exc:
        result = {"ok": False, "error": {
            "type": type(exc).__name__, "message": limited(exc)[0],
            "traceback": limited(traceback.format_exc())[0],
        }}
    result_path.write_text(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
