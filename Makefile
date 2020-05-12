.PHONY: build lint start test

build:
	pipenv install --dev

lint:
	pipenv run flake8 ./ras_party ./test
	# pipenv check ./ras_party ./test

test: lint
	APP_SETTINGS=TestingConfig pipenv run pytest test --cov ras_party --cov-report term-missing

start:
	pipenv run python3 run.py
