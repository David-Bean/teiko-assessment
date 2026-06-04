.PHONY: setup pipeline dashboard

setup:
	pip install -r requirements.txt

pipeline:
	rm -f *.db
	rm -f outputs/*
	mkdir -p outputs
	python load_data.py
	python analysis.py

dashboard:
	streamlit run app.py
