class SPARQL:
    PREFIXES = '\nPREFIX geosparql: <http://www.opengis.net/ont/geosparql#>\n' \
               'PREFIX  geof: <http://www.opengis.net/def/function/geosparql/>\n' \
               'PREFIX db: <http://spatial.au/ontology#>\n' \
               'PREFIX spatialF: <http://jena.apache.org/function/spatial#>\n' \
               'PREFIX units: <http://www.opengis.net/def/uom/OGC/1.0/>\n' \
               'PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n' \
               'PREFIX owl:<http://www.w3.org/2002/07/owl#>\n\n'

    DEFINE_SIMPLE = '\t?<PI> db:has_name ?<PI>NAME; \n' \
                    '\t\tgeosparql:hasGeometry ?<PI>GEOM. \n' \
                    '\tOPTIONAL{?<PI> db:has_osm_id ?<PI>ID}. \n' \
                    '\tfilter(regex(?<PI>NAME, \"<PIVALUE>\", \"i\" )) .\n'

    GENERAL_FORMAT_ASK = PREFIXES+'ASK {\n' \
                         '<ASK>\n}'

    GENERAL_FORMAT_SIMPLE_FUNCTION = PREFIXES + "SELECT <FUNCTION> \n" \
                                                "WHERE { \n" \
                                                "<WHERE>}\n" \
                                                " LIMIT <LIMIT>";

    GENERAL_FORMAT_SORT_FUNCTION = PREFIXES + "SELECT <SELECT> \n" \
                                              "WHERE { \n" \
                                              "<WHERE>}\n" \
                                              "<SORT>\n LIMIT <LIMIT>"

    TOPIC_DEFINITION = '\t?<PI> <http://spatial.au/ontology#<TOPIC>> ?<PI><TOPIC>. \n'

    GENERAL_FORMAT = PREFIXES + "SELECT <PILIST> \n" \
                                "WHERE { \n<WHERE>" \
                                "}\n LIMIT <LIMIT>"

    DEFINE_TYPE = '\t?<PI> <http://spatial.au/ontology#has_fclass> ?<PI>TYPE;\n' \
                  '\t\t<http://www.opengis.net/ont/geosparql#hasGeometry> ?<PI>GEOM;\n' \
                  '\t\t<http://spatial.au/ontology#has_name> ?<PI>NAME.\n' \
                  '\tOPTIONAL{?<PI> db:has_osm_id ?<PI>ID}. \n' \
                  '\tfilter(regex(?<PI>TYPE, \"<PTVALUE>\", \"i\" )) .\n'

    DEFINE_TYPE_EXEMPT = '\tFILTER NOT EXISTS { ?<PI> (owl:sameAs|^owl:sameAs) ?<EX>}. \n'

    OBJECT_RELATION = ''
