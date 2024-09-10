.PHONY: build clean down format lint lock_dependencies requirements run_testt sort test up

#################################################################################
# GLOBALS                                                                       #
#################################################################################

PROJECT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
SHELL:=/bin/bash
PROFILE = default
PROJECT_NAME = jumpcutter
PYTHON_INTERPRETER = python
DOCKER_COMPOSE_RUN = docker compose run -w /app --rm app
lock_dependencies: BUILD_POETRY_LOCK = ~/poetry.lock.build


#################################################################################
# COMMANDS                                                                      #
#################################################################################

## Build docker containers with docker-compose
build: 
	docker-compose build

## docker-compose up -d
up:
	docker-compose up -d

## docker-compose down
down:
	docker-compose down

## docker exec -it jumpcutter-app bash
exec-in: up
	docker exec -it jumpcutter-app bash

## Delete all compiled Python files
clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete

## Lint using pylama, isort and black
lint:
	$(DOCKER_COMPOSE_RUN) bash -c "pylama && isort --check-only --atomic ./jumpcutter && black --check ./jumpcutter"

## Sort imports
sort:
	$(DOCKER_COMPOSE_RUN) isort --atomic ./jumpcutter

## Format code with black
format:
	$(DOCKER_COMPOSE_RUN) black ./jumpcutter


## Check type annotations
check-type-annotations:
	$(DOCKER_COMPOSE_RUN) mypy ./jumpcutter

## Lock dependencies with pipenv
lock_dependencies:
	docker-compose run --rm -w /app app bash -c "if [ -e $(BUILD_POETRY_LOCK) ]; then cp $(BUILD_POETRY_LOCK) ./poetry.lock; else poetry lock; fi"

## Package the code and share it on PyPi
package:
	docker-compose run --rm app poetry publish --build


#################################################################################
# PROJECT RULES                                                                 #
#################################################################################



#################################################################################
# Self Documenting Commands                                                     #
#################################################################################

.DEFAULT_GOAL := help

# Inspired by <http://marmelab.com/blog/2016/02/29/auto-documented-makefile.html>
# sed script explained:
# /^##/:
# 	* save line in hold space
# 	* purge line
# 	* Loop:
# 		* append newline + line to hold space
# 		* go to next line
# 		* if line starts with doc comment, strip comment character off and loop
# 	* remove target prerequisites
# 	* append hold space (+ newline) to line
# 	* replace newline plus comments by `---`
# 	* print line
# Separate expressions are necessary because labels cannot be delimited by
# semicolon; see <http://stackoverflow.com/a/11799865/1968>
.PHONY: help
help:
	@echo "$$(tput bold)Available rules:$$(tput sgr0)"
	@echo
	@sed -n -e "/^## / { \
		h; \
		s/.*//; \
		:doc" \
		-e "H; \
		n; \
		s/^## //; \
		t doc" \
		-e "s/:.*//; \
		G; \
		s/\\n## /---/; \
		s/\\n/ /g; \
		p; \
	}" ${MAKEFILE_LIST} \
	| LC_ALL='C' sort --ignore-case \
	| awk -F '---' \
		-v ncol=$$(tput cols) \
		-v indent=19 \
		-v col_on="$$(tput setaf 6)" \
		-v col_off="$$(tput sgr0)" \
	'{ \
		printf "%s%*s%s ", col_on, -indent, $$1, col_off; \
		n = split($$2, words, " "); \
		line_length = ncol - indent; \
		for (i = 1; i <= n; i++) { \
			line_length -= length(words[i]) + 1; \
			if (line_length <= 0) { \
				line_length = ncol - indent - length(words[i]) - 1; \
				printf "\n%*s ", -indent, " "; \
			} \
			printf "%s ", words[i]; \
		} \
		printf "\n"; \
	}' \
	| more $(shell test $(shell uname) = Darwin && echo '--no-init --raw-control-chars')
