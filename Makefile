.PHONY: install load notebook clean help

help:
	@echo "make install   installe l'environnement (Python 3.11 via uv)"
	@echo "make load      extrait les donnees Deezer vers data/raw/ (~12 min)"
	@echo "make notebook  ouvre le notebook de demarche (analyse/)"
	@echo "make clean     supprime la zone brute"

install:
	uv sync

load:
	uv run python load.py

notebook:
	uv run jupyter lab analyse/demarche.ipynb

clean:
	rm -rf data/raw
