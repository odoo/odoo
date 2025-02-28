default : clean dist

phony: test

test:
	pytest

htmlcov:
	pytest --cov=pdf417gen --cov-report=html

dist:
	python -m build

clean:
	rm -rf build dist *.egg-info MANIFEST htmlcov

publish:
	twine upload dist/*
