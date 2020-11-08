class SPARQLTemplates:
    PREFIXES = '\nPREFIX geosparql: <http://www.opengis.net/ont/geosparql#>\n' \
               'PREFIX  geof: <http://www.opengis.net/def/function/geosparql/>\n' \
               'PREFIX db: <http://spatial.au/ontology#>\n' \
               'PREFIX spatialF: <http://jena.apache.org/function/spatial#>\n' \
               'PREFIX units: <http://www.opengis.net/def/uom/OGC/1.0/>\n' \
               'PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n' \
               'PREFIX owl:<http://www.w3.org/2002/07/owl#>\n\n'

    DEFINE_CONCEPT = '\t?<PI> a db:<CONCEPT> .\n' \
                    '\t?<PI> db:has_name ?<PI>NAME; \n' \
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

    OBJECT_RELATION = '\t?<PI> <OBJ_REL> ?<OBJECT>. \n' \
                      '\t?<OBJECT> <http://spatial.au/ontology#has_name> ?<OBJECT>NAME;\n' \
                      '\t\tfilter(regex(?<OBJECT>NAME, \"<OBJECT_NAME>\", \"i\" )). \n'

    KNOWN_RESOURCES = '\t?<PI> VALUES {<?<PIURI>>}. \n'

    ATTRIBUTE_RELATION = '\t?<PI> <http://spatial.au/ontology#has_<ATTRIBUTE>> ?<OBJECT>.\n'

    DISTANCE_ATTRIBUTE = '\t?<OBJECT> geof:distance(?<PI1>GEOM ?<PI2>GEOM units:<UNIT>).\n'

    DISTANCE_RELATIONSHIP = '\tFILTER(geof:distance(<PI1>GEOM, <PI2>GEOM, <UNIT>) < <DISTANCE>).\n'

    SPATIAL_RELATION_MAPPING = {'in': '\t<PI1>GEOM geosparql:ehCoveredBy <PI2>GEOM.\n',
                                'near': '\tFILTER (geof:distance(<PI1>GEOM, <PI2>GEOM, units:metre) < 5000).\n',
                                'close to': '\tFILTER (geof:distance(<PI1>GEOM, <PI2>GEOM, units:metre) < 5000).\n',
                                'north of': '\tFILTER (spatialF:northGeom(<PI1>GEOM, <PI2>GEOM, 10)).\n',
                                'south of': '\tFILTER (spatialF:southGeom(<PI1>GEOM, <PI2>GEOM, 10)).\n',
                                'east of': '\tFILTER (spatialF:eastGeom(<PI1>GEOM, <PI2>GEOM, 10)).\n',
                                'west of': '\tFILTER (spatialF:westGeom(<PI1>GEOM, <PI2>GEOM, 10)).\n',
                                'border': '\tFILTER(geof:sfTouches(<PI1>GEOM,<PI2>GEOM)).\n',
                                'cross': '\tFILTER(geof:sfCrosses(<PI1>GEOM,<PI2>GEOM)).\n',
                                'OTHER': '\tFILTER(geof:sfIntersects(<PI1>GEOM,<PI2>GEOM)).\n'}


class SPARQLGenerator:
    def __init__(self, dependencies):
        self.dependencies = dependencies
        self.concept_varids = {}

    def to_SPARQL(self):
        # define var_ids for concepts

        # use declaration to define vars in where-clause
        # use criteria to bound them in where-clause

        # use intent to construct select/ask statements
        # define overall template (sorting?) (functions?)
        return 'TODO'

    @staticmethod
    def define_concept(dependency, varid):
        template = SPARQLTemplates.DEFINE_CONCEPT
        template = template.replace('<PI>', varid)
        template = template.replace('<CONCEPT>', dependency.arg2.name)
        template = template.replace('<PIVALUE>', dependency.arg1.name)
        return template

    @staticmethod
    def define_variable(dependency):
        template = SPARQLTemplates.DEFINE_TYPE
        template = template.replace('<PI>', dependency.arg2.name)
        template = template.replace('<PIVALUE>', dependency.arg1.name)
        return template

    def define_attribute(self, dependency):
        # todo
        return

    def define_spatial_relationship(self, dependency):
        # todo
        return

    def define_situations(self, dependency):
        # todo
        return

    def construct_where(self):
        # todo
        return

    def construct_select_ask(self):
        # todo
        return

    @staticmethod
    def define_sort(dependency):
        # todo
        return

    @staticmethod
    def define_comparison(dependency):
        # todo
        return