# Harnice Aerospace Connector Library

If you would like to add part families to this library, either submit a PR yourself, or create an issue with the details you'd like to see.

## Generating the library

Each family emitter writes its entire catalog. `generate_all_in_repo.py` runs every `*_generator.py`.

```bash
python generate_all_in_repo.py     # entire library
python D38999/d38999_generator.py  # one family
python check.py                    # CI merge gate
```

`check.py` runs `generate_all_in_repo.py` and fails if git sees a diff against the tree being merged. That CI job is disabled because a full library generate is too slow.
