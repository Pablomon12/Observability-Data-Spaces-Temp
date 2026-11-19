# Ontología de observabilidad en espacios de datos

Perfil RDF/OWL para reconstruir intercambios del plano de control, correlacionarlos con la telemetría de los conectores y documentar mediciones de calidad de los datos. Es una revisión independiente de `Observability_Ontology` (`fdf4074`).

## Archivos

| Archivo | Contenido |
| --- | --- |
| [ontology/observability.ttl](ontology/observability.ttl) | Fuente canónica del módulo OWL |
| [shapes/observability.shacl.ttl](shapes/observability.shacl.ttl) | Requisitos para instancias, con SHACL Core y SHACL-SPARQL |
| [examples/olivar.ttl](examples/olivar.ttl) | Consulta de catálogo, negociación con y sin acuerdo, transferencias, evaluación, logs, spans y mediciones |
| [queries/](queries/) | Consultas SPARQL de auditoría e historial |
| [tests/](tests/) | Pruebas del ejemplo, casos que deben rechazarse y regresiones de vocabulario |
| [tools/](tools/) | Comprobación OWL reproducible con un razonador HermiT disponible localmente |

## Criterios del modelo

- **Intercambios.** Cada interacción de catálogo, negociación y transferencia tiene un IRI de correlación RDF. Los identificadores DSP de consumidor y proveedor se conservan por separado como literales. Cada proceso enlaza su espacio de datos y sus dos participantes por rol. La transferencia enlaza el acuerdo ODRL que la rige, y el acuerdo apunta al mismo dataset, según el perfil compacto usado en DSP 2025-1.
- **Estados observados.** Cada registro DSP conserva el proceso, el estado, el conector de origen y el instante del hecho. La atribución del registro puede corresponder a un observador independiente. Las listas de estados son específicas para negociación y transferencia. El historial puede contener huecos y varias observaciones del mismo estado. Las categorías de catálogo `REQUEST`, `RESPONSE` y `ERROR` describen registros del perfil local.
- **Telemetría.** Un registro de log puede indicar el instante del hecho o el instante de observación. Una traza agrupa spans identificados dentro de ella. Un log puede conservar el identificador de un span que todavía no esté en el grafo. Cada span declara su intervalo, su conector de origen y, cuando se conoce y está en el grafo, su padre. Las muestras operativas usan una definición de métrica y un valor decimal. El estado de salud de un conector es una observación operativa independiente de DSP.
- **Políticas y calidad.** Una evaluación registra el resultado comunicado, la política y, si procede, una regla explícita. `prov:wasDerivedFrom` permite enlazar evidencia con IRI. El conjunto de datos y su medición de calidad se vinculan mediante DQV. Una latencia del conector se registra como telemetría operativa.

Los requisitos de completitud y cardinalidad están en SHACL. Para aplicarlos, incluye los tipos RDF de los recursos y la descripción local de los nodos referenciados que las reglas necesitan inspeccionar. El módulo OWL se carga sin dependencias remotas. Usa declaraciones de clases externas para conservar su identidad y formula los axiomas de dominio, rango y subclase sobre términos propios.

El perfil usa los estados de DSP 2025-1 para registrar observaciones. La validación abarca los estados aplicables y la correlación de registros. La comprobación del orden legal de todas las transiciones, de los mensajes de red, de la autenticidad de las evidencias y del cumplimiento de la política corresponde al sistema que genera los registros. La pertenencia de una regla a una política se verifica contra sus enlaces explícitos en el grafo, con soporte para deberes enlazados directamente desde permisos.

El espacio de nombres `https://example.org/dataspace-observability/ontology#` es **local y provisional**. Los IRIs del espacio `examples/` y sus identificadores son sintéticos. Antes de publicar una versión interoperable, selecciona un dominio bajo tu control y cambia de forma coordinada los IRIs del módulo, las formas, los datos de ejemplo y las consultas.

## Validación y consultas

Con Python 3.10 o posterior, desde la raíz del repositorio:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pyshacl -s shapes/observability.shacl.ttl -e ontology/observability.ttl -m examples/olivar.ttl
python -m unittest discover -s tests -v
```

La primera validación devuelve `Conforms: True`. Las pruebas modifican copias del ejemplo para comprobar el rechazo de datos inválidos. Con el ejemplo y la consulta de auditoría se obtiene la relación entre `log-lectura`, `conector-proveedor`, `transferencia-2`, `acuerdo`, `datos-iot` y `span-proveedor`.

```sh
python - <<'PY'
from pathlib import Path

from rdflib import Graph

graph = Graph().parse("examples/olivar.ttl", format="turtle")
query = Path("queries/auditar-transferencia.rq").read_text(encoding="utf-8")
print(graph.query(query).serialize(format="csv").decode("utf-8"), end="")
PY
```

### Comprobación OWL con HermiT

El módulo se puede abrir en Protégé y comprobar con HermiT. Para ejecutar el verificador por consola, usa Java 11 o posterior y configura `OWL_REASONER_CLASSPATH` con los JAR de HermiT, OWLAPI y sus dependencias. El verificador comprueba el perfil OWL 2 DL del módulo, la consistencia, las clases insatisfacibles y las clasificaciones globales PROV.

```sh
python tools/assemble_owl.py /tmp/obs-modulo.rdf
java -cp "$OWL_REASONER_CLASSPATH" tools/CheckOwl.java /tmp/obs-modulo.rdf
```

También se puede comprobar el ejemplo junto con vocabularios externos suministrados como ficheros locales. Esta prueba utiliza la unión explícita de los grafos indicados. La herramienta omite las declaraciones de importación de los ficheros adicionales para que el razonador trabaje sobre esa unión sin acceder a la red. `--reason-only` comprueba la consistencia de la unión y las inferencias indicadas, ya que los artefactos externos pueden contener axiomas fuera del perfil OWL 2 DL.

```sh
python tools/assemble_owl.py /tmp/obs-integrado.rdf \
  --turtle examples/olivar.ttl --turtle /ruta/prov-o.ttl \
  --rdfxml /ruta/ODRL22.rdf --rdfxml /ruta/dcat3.rdf
java -cp "$OWL_REASONER_CLASSPATH" tools/CheckOwl.java /tmp/obs-integrado.rdf --reason-only
```

La revisión inicial pasó ambas comprobaciones con HermiT 1.4.3.456. La segunda usó las copias de PROV-O, ODRL y DCAT suministradas en el repositorio de partida. Allí `prov-o.rdf` contiene Turtle y se debe pasar con `--turtle`.

## Migración desde el modelo anterior

| Término o patrón anterior | Criterio para migrarlo |
| --- | --- |
| `Contrato` | Identifica el proceso con `obs:ContractNegotiation`, el documento con `odrl:Agreement` y el hecho registrado con una observación de estado. |
| `Ejecucion` y `transferProcessID` en la traza | Usa `obs:TransferProcess` para el proceso del plano de control y coloca los identificadores de cada parte en ese proceso. Retén la instrumentación del plano de datos en sus registros y spans. |
| `SovereignAgent`, `DataSpaceUser` | Usa `obs:Participant` y declara los roles por proceso. La relación con un dataset debe reflejar el hecho que se pueda documentar, como atribución o condiciones de uso. |
| `ExecutionLog`, `LogObservation`, `compliesWith` | Usa `obs:LogRecord` para la señal y `obs:PolicyEvaluation` para una evaluación que conste en los datos. Conserva el origen y la hora. |
| `LatencyMetric`, `ComponentStatus` | Usa una definición y una muestra para una latencia. Registra la salud del conector con `obs:ConnectorHealthRecord`. |
| Recursos identificados por URLs de secciones de documentación | Usa las IRIs de vocabulario de la tabla siguiente. Migra los recursos según su significado y revisa las inferencias. |

## Términos externos y fuentes primarias

Las IRIs de la tabla son los espacios de nombres usados en RDF. Los enlaces llevan a las especificaciones donde se definen los términos. El test de vocabulario vigila los términos de dominio empleados en el esquema, las formas y el ejemplo.

| Espacio de nombres | Términos reutilizados | Fuente |
| --- | --- | --- |
| `http://www.w3.org/ns/prov#` | `Activity`, `Entity`, `Agent`, `SoftwareAgent`, `wasAttributedTo`, `wasDerivedFrom` | [W3C PROV-O](https://www.w3.org/TR/prov-o/) |
| `http://www.w3.org/ns/dcat#` | `Catalog`, `Dataset`, `Distribution`, `dataset` | [W3C DCAT 3](https://www.w3.org/TR/vocab-dcat-3/) |
| `http://www.w3.org/ns/dqv#` | `QualityMeasurement`, `Metric`, `Dimension`, `computedOn`, `isMeasurementOf`, `inDimension`, `value` | [W3C DQV](https://www.w3.org/TR/vocab-dqv/) |
| `http://www.w3.org/ns/odrl/2/` | `Policy`, `Agreement`, `Offer`, `Rule`, `Permission`, `Prohibition`, `Duty`, `Party`, `Asset`, `target`, `assigner`, `assignee`, `permission`, `prohibition`, `obligation`, `duty`, `action`, `use` | [W3C ODRL Vocabulary 2.2](https://www.w3.org/TR/odrl-vocab/), [ODRL Information Model 2.2](https://www.w3.org/TR/odrl-model/) |

Los valores de `obs:dspState` proceden de los protocolos de [negociación](https://github.com/eclipse-dataspace-protocol-base/DataspaceProtocol/blob/2025-1/specifications/negotiation/contract.negotiation.protocol.md) y [transferencia](https://github.com/eclipse-dataspace-protocol-base/DataspaceProtocol/blob/2025-1/specifications/transfer/transfer.process.protocol.md) en el tag `2025-1` de Eclipse. Los identificadores de traza y span siguen la representación hexadecimal de la [API de trazas de OpenTelemetry](https://opentelemetry.io/docs/specs/otel/trace/api/#retrieving-the-traceid-and-spanid). La distinción entre instante de origen e instante observado se basa en su [modelo de logs](https://opentelemetry.io/docs/specs/otel/logs/data-model/). Ambos mapeos usan términos propios de este proyecto.

El alcance de observabilidad toma como referencia [Observability in Data Spaces, IDSA, versión 1.0](https://baidata.eu/media/1/IDSA-Position-Paper-Observability-in-Data-Spaces.pdf). La validación y las consultas se basan en [SHACL](https://www.w3.org/TR/shacl/) y [SPARQL 1.1](https://www.w3.org/TR/sparql11-query/).
