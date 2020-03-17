# Contributing

## Development Workflow

Puter is a cli, which is handled by Click and Poetry.  In order to get the `puter`
cli on your path, start with:

* `poetry install`

Then, depending on your setup, you can invoke `puter` directly using either:

* `poetry run puter`

or (if you've got direnv and poetry set up together) simply

* `puter`

## Pushing and Merging a branch

When a branch is pushed or merged, CI will compile the project, check formatting, and run tests
and static analysis.

## Follow Patterns

When adding something, first look for other implementations in the repository, and mirror those.
