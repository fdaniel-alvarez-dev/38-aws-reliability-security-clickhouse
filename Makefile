.PHONY: setup demo demo-offline lab-up lab-down lab-logs lab-load-demo lab-query test test-demo test-production clean

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

demo: demo-offline

demo-offline:
	python3 pipelines/pipeline_demo.py

lab-up:
	docker compose up -d

lab-down:
	docker compose down -v

lab-logs:
	docker compose logs -f --tail=200

lab-load-demo:
	bash scripts/lab_load_demo.sh

lab-query:
	bash scripts/lab_query.sh

test:
	$(MAKE) test-demo

test-demo:
	TEST_MODE=demo python3 tests/run_tests.py

test-production:
	TEST_MODE=production PRODUCTION_TESTS_CONFIRM=1 python3 tests/run_tests.py

clean:
	rm -rf .venv data/processed artifacts pipelines/__pycache__ tests/__pycache__
