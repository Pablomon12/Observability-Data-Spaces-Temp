import java.io.File;

import org.semanticweb.HermiT.ReasonerFactory;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.model.IRI;
import org.semanticweb.owlapi.profiles.OWL2DLProfile;

class CheckOwl {
    private static final String PROV = "http://www.w3.org/ns/prov#";

    public static void main(String[] args) throws Exception {
        boolean checkProfile = args.length == 1;
        if (args.length == 0 || (args.length != 1 && !(args.length == 2 && args[1].equals("--reason-only")))) {
            throw new IllegalArgumentException("Uso: CheckOwl.java <grafo.rdf> [--reason-only]");
        }

        var manager = OWLManager.createOWLOntologyManager();
        var ontology = manager.loadOntologyFromOntologyDocument(new File(args[0]));
        if (checkProfile) {
            var profile = new OWL2DLProfile().checkOntology(ontology);
            if (!profile.isInProfile()) {
                throw new IllegalStateException(profile.toString());
            }
            System.out.println("Perfil OWL 2 DL correcto");
        }

        var reasoner = new ReasonerFactory().createReasoner(ontology);
        try {
            if (!reasoner.isConsistent()) {
                throw new IllegalStateException("Grafo OWL inconsistente");
            }
            var unsatisfiable = reasoner.getUnsatisfiableClasses().getEntitiesMinusBottom();
            if (!unsatisfiable.isEmpty()) {
                throw new IllegalStateException("Clases insatisfacibles: " + unsatisfiable);
            }
            var factory = manager.getOWLDataFactory();
            for (String localName : new String[]{"Agent", "Activity", "Entity"}) {
                var provClass = factory.getOWLClass(IRI.create(PROV + localName));
                var globalType = factory.getOWLSubClassOfAxiom(factory.getOWLThing(), provClass);
                if (reasoner.isEntailed(globalType)) {
                    throw new IllegalStateException("Clasificación global inesperada: " + provClass);
                }
            }
            System.out.println("Grafo consistente, clases satisfacibles y sin clasificación global PROV");
        } finally {
            reasoner.dispose();
        }
    }
}
