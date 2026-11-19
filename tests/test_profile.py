import unittest
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCAT, OWL, PROV, RDF, RDFS, SH, XSD

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://example.org/dataspace-observability/"
OBS = Namespace(BASE + "ontology#")
EX = Namespace(BASE + "examples/olivar/")
ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
DQV = Namespace("http://www.w3.org/ns/dqv#")


def read_graph(path):
    return Graph().parse(ROOT / path, format="turtle")


class ProfileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = read_graph("ontology/observability.ttl")
        cls.shapes = read_graph("shapes/observability.shacl.ttl")

    def setUp(self):
        self.data = read_graph("examples/olivar.ttl")

    def validate(self, **options):
        return validate(
            self.data, shacl_graph=self.shapes, ont_graph=self.ontology, **options
        )

    def assert_violation(self, node, component=None, path=None):
        conforms, report, message = self.validate()
        self.assertFalse(conforms, message)
        results = list(report.subjects(SH.focusNode, node))
        if component is not None:
            results = [
                result for result in results
                if (result, SH.sourceConstraintComponent, component) in report
            ]
        if path is not None:
            results = [
                result for result in results if (result, SH.resultPath, path) in report
            ]
        self.assertTrue(results, message)

    def run_query(self, filename):
        query = (ROOT / "queries" / filename).read_text(encoding="utf-8")
        return list(self.data.query(query))

    def test_example_and_shapes_are_valid(self):
        conforms, _, message = self.validate(meta_shacl=True)
        self.assertTrue(conforms, message)

    def test_missing_agreement(self):
        self.data.remove((EX["transferencia-2"], OBS.underAgreement, None))
        self.assert_violation(EX["transferencia-2"], SH.MinCountConstraintComponent, OBS.underAgreement)

    def test_missing_process_identifiers(self):
        process = EX["transferencia-2"]
        self.data.remove((process, OBS.consumerProcessId, None))
        self.data.remove((process, OBS.providerProcessId, None))
        self.assert_violation(process, SH.OrConstraintComponent)

    def test_agreement_for_another_dataset(self):
        other = EX["datos-alternativos"]
        self.data.add((other, RDF.type, DCAT.Dataset))
        self.data.set((EX["transferencia-2"], OBS.dataset, other))
        self.assert_violation(EX["transferencia-2"], SH.EqualsConstraintComponent)

    def test_finalized_negotiation_requires_an_agreement(self):
        self.data.remove((EX.negociacion, OBS.resultingAgreement, None))
        self.assert_violation(EX["negociacion-finalizada"], SH.OrConstraintComponent)

    def test_wrong_state_for_process(self):
        self.data.set((EX["transferencia-suspendida"], OBS.dspState, Literal("FINALIZED")))
        self.assert_violation(EX["transferencia-suspendida"], SH.InConstraintComponent, OBS.dspState)

    def test_wrong_process_kind_for_record(self):
        self.data.set((EX["transferencia-suspendida"], OBS.aboutProcess, EX.negociacion))
        self.assert_violation(EX["transferencia-suspendida"], SH.ClassConstraintComponent, OBS.aboutProcess)

    def test_unknown_or_unrelated_rule(self):
        self.data.add((EX["otro-permiso"], RDF.type, ODRL.Permission))
        self.data.set((EX.evaluacion, OBS.evaluatedRule, EX["otro-permiso"]))
        self.assert_violation(EX.evaluacion, SH.SPARQLConstraintComponent)

    def test_source_timestamp_needs_a_timezone(self):
        record = EX["transferencia-suspendida"]
        self.data.set((record, OBS.occurredAt, Literal("2026-01-20T09:03:39", datatype=XSD.dateTime)))
        self.assert_violation(record, SH.NodeConstraintComponent, OBS.occurredAt)

    def test_log_can_use_observed_time_and_missing_span(self):
        log = EX["log-lectura"]
        self.data.remove((log, OBS.occurredAt, None))
        self.data.remove((EX["span-proveedor"], None, None))
        recorded = Literal("2026-01-20T09:03:40Z", datatype=XSD.dateTime)
        self.data.add((log, OBS.observedAt, recorded))
        conforms, _, message = self.validate()
        self.assertTrue(conforms, message)
        row, = self.run_query("auditar-transferencia.rq")
        self.assertEqual(row.fecha, recorded)
        self.assertIsNone(row.span)
        self.assertIsNotNone(row.traceId)

    def test_log_with_span_id_requires_trace(self):
        self.data.remove((EX["log-lectura"], OBS.inTrace, None))
        self.assert_violation(EX["log-lectura"], SH.OrConstraintComponent)

    def test_trace_id_must_be_nonzero(self):
        self.data.set((EX.traza, OBS.traceId, Literal("0" * 32)))
        self.assert_violation(EX.traza, SH.NotConstraintComponent, OBS.traceId)

    def test_duplicate_trace_id(self):
        other = EX["otra-traza"]
        self.data.add((other, RDF.type, OBS.Trace))
        self.data.add((other, OBS.traceId, self.data.value(EX.traza, OBS.traceId)))
        self.assert_violation(other, SH.SPARQLConstraintComponent)

    def test_duplicate_span_id_in_same_trace(self):
        parent = EX["span-consumidor"]
        child = EX["span-proveedor"]
        self.data.set((child, OBS.spanId, self.data.value(parent, OBS.spanId)))
        self.assert_violation(child, SH.SPARQLConstraintComponent)

    def test_span_parent_from_another_trace(self):
        child = EX["span-proveedor"]
        other = EX["otra-traza"]
        self.data.add((other, RDF.type, OBS.Trace))
        self.data.add((other, OBS.traceId, Literal("1" * 32)))
        self.data.set((child, OBS.inTrace, other))
        self.assert_violation(child, SH.SPARQLConstraintComponent)

    def test_span_parent_cycle(self):
        parent = EX["span-consumidor"]
        self.data.add((parent, OBS.parentSpan, EX["span-proveedor"]))
        self.assert_violation(parent, SH.SPARQLConstraintComponent)

    def test_span_end_before_start(self):
        span = EX["span-proveedor"]
        self.data.set((span, OBS.spanEndedAt, Literal("2026-01-20T09:00:00Z", datatype=XSD.dateTime)))
        self.assert_violation(span, SH.LessThanOrEqualsConstraintComponent, OBS.spanStartedAt)

    def test_health_and_transfer_states_are_distinct(self):
        self.data.set((EX["salud-proveedor"], OBS.healthState, Literal("SUSPENDED")))
        self.assert_violation(EX["salud-proveedor"], SH.InConstraintComponent, OBS.healthState)

    def test_technical_metric_requires_numeric_value(self):
        sample = EX["latencia-observada"]
        self.data.set((sample, OBS.numericValue, Literal("150 ms")))
        self.assert_violation(sample, SH.DatatypeConstraintComponent, OBS.numericValue)

    def test_dqv_measurement_is_not_an_operational_sample(self):
        quality_record = EX["calidad-datos"]
        self.data.remove((quality_record, DQV.isMeasurementOf, None))
        self.assert_violation(quality_record, SH.MinCountConstraintComponent, DQV.isMeasurementOf)
        self.assertNotIn((quality_record, RDF.type, OBS.MetricSample), self.data)

    def test_audit_query_joins_log_process_agreement_and_span(self):
        row, = self.run_query("auditar-transferencia.rq")
        self.assertEqual(row.log, EX["log-lectura"])
        self.assertEqual(row.conector, EX["conector-proveedor"])
        self.assertEqual(row.proceso, EX["transferencia-2"])
        self.assertEqual(row.acuerdo, EX.acuerdo)
        self.assertEqual(row.dataset, EX["datos-iot"])
        self.assertEqual(row.span, EX["span-proveedor"])

    def test_history_keeps_terminated_negotiation_without_agreement(self):
        rows = self.run_query("historial-estados.rq")
        by_record = {row.registro: row for row in rows}
        self.assertEqual(len(rows), 6)
        terminated = by_record[EX["negociacion-terminada"]]
        self.assertEqual(str(terminated.estado), "TERMINATED")
        self.assertIsNone(terminated.acuerdo)
        self.assertEqual(str(by_record[EX["transferencia-suspendida"]].estado), "SUSPENDED")
        self.assertEqual(str(by_record[EX["transferencia-completada"]].estado), "COMPLETED")

    def test_schema_preserves_activity_and_record_distinction(self):
        graph = self.ontology
        self.assertIn((OBS.ExchangeProcess, RDFS.subClassOf, PROV.Activity), graph)
        self.assertIn((OBS.ObservationRecord, RDFS.subClassOf, PROV.Entity), graph)
        self.assertIn((OBS.ObservationRecord, OWL.disjointWith, PROV.Activity), graph)
        self.assertFalse(any(OWL.topObjectProperty in triple for triple in graph))
        self.assertFalse(any(graph.triples((None, OWL.equivalentClass, None))))
        self.assertFalse(any(graph.triples((None, OWL.imports, None))))
        for subject, predicate, obj in graph:
            if isinstance(subject, URIRef) and not str(subject).startswith(BASE):
                self.assertEqual((predicate, obj), (RDF.type, OWL.Class))

    def test_external_domain_terms_match_reviewed_allowlist(self):
        allowed = {
            str(DCAT): {"Catalog", "Dataset", "Distribution", "dataset"},
            str(DQV): {"QualityMeasurement", "Metric", "Dimension", "computedOn",
                       "isMeasurementOf", "inDimension", "value"},
            str(ODRL): {"Agreement", "Offer", "Policy", "Rule", "Permission", "Prohibition",
                        "Duty", "Party", "Asset", "target", "assigner", "assignee",
                        "permission", "prohibition", "obligation", "duty", "action", "use"},
            str(PROV): {"Agent", "Activity", "Entity", "SoftwareAgent",
                        "wasAttributedTo", "wasDerivedFrom"},
        }
        infrastructure = (
            BASE, str(RDF), str(RDFS), str(OWL), str(SH), str(XSD)
        )
        for graph in (self.ontology, self.shapes, self.data):
            for iri in (term for triple in graph for term in triple if isinstance(term, URIRef)):
                value = str(iri)
                if value.startswith(infrastructure):
                    continue
                self.assertTrue(
                    any(value.startswith(prefix) and value[len(prefix):] in terms
                        for prefix, terms in allowed.items()), value
                )
