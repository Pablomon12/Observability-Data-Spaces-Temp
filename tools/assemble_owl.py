"""Build an explicit RDF/XML graph for offline OWL reasoning."""

import argparse
from pathlib import Path

from rdflib import Graph, OWL, RDF

SCHEMA = Path(__file__).resolve().parents[1] / "ontology/observability.ttl"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--turtle", type=Path, action="append", default=[])
    parser.add_argument("--rdfxml", type=Path, action="append", default=[])
    args = parser.parse_args()

    graph = Graph().parse(SCHEMA, format="turtle")
    for paths, rdf_format in ((args.turtle, "turtle"), (args.rdfxml, "xml")):
        for path in paths:
            source = Graph().parse(path, format=rdf_format)
            # Only include the selected input graphs. Keep the canonical ontology header.
            source.remove((None, OWL.imports, None))
            source.remove((None, RDF.type, OWL.Ontology))
            graph += source
    graph.serialize(destination=args.output, format="xml")


if __name__ == "__main__":
    main()
