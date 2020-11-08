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
                                'of': '\t<PI1>GEOM geosparql:ehCoveredBy <PI2>GEOM.\n',
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
    COMPLEX_RELATIONSHIPS = ['within \d.* ',
                                    'at most \d.* ',
                                    'less than \d.* away ',
                                    'more than \d.* away ',
                                    'in \d.* radius ',
                                    'in a range of \d.* ',
                                    'in the range of \d.* ']

    def __init__(self, dependencies, variables):
        self.dependencies = dependencies
        self.variables = variables

        self.concept_varids = {}

    def to_SPARQL(self):
        result = ''
        # use declaration to define vars in where-clause
        # use criteria to bound them in where-clause
        where_clause = self.construct_where()

        # use intent to construct select/ask statements
        # define overall template (sorting?) (functions?)

        # todo dummy
        result = SPARQLTemplates.GENERAL_FORMAT.replace('<WHERE>', where_clause)

        # return the results
        return result

    def declare(self):
        declare_statments = ''
        varid = 0
        declarations = self.dependencies['declaration']
        for declaration in declarations:
            if declaration.arg2.nodeType == 'VARIABLE':
                 declare_statments += SPARQLGenerator.define_variable(declaration)
            else:
                self.concept_varids[declaration.arg1.name] = 'c'+str(varid)
                varid += 1
                declare_statments += SPARQLGenerator.define_concept(declaration,
                                                                    self.concept_varids[declaration.arg1.name])
        return declare_statments

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
        template = template.replace('<PTVALUE>', dependency.arg1.name)
        return template

    def define_attribute(self, dependency):
        # todo
        return

    def find_var(self, string):
        if string in self.variables.keys():
            return self.variables[string]
        return self.concept_varids[string]

    def define_spatial_relationship(self, dependency, distance=False, binary=True):
        template = ''
        var1 = self.find_var(dependency.arg1.name)
        var2 = self.find_var(dependency.arg2.name)
        if binary and not distance:
            if dependency.relation.name in SPARQLTemplates.SPATIAL_RELATION_MAPPING.keys():
                template = SPARQLTemplates.SPATIAL_RELATION_MAPPING[dependency.relation.name]
                template = template.replace("<PI1>", var1).replace("<PI2>", var2)
        elif distance:
            template = SPARQLTemplates.DISTANCE_RELATIONSHIP
            template = template.replace("<PI1>", var1).replace("<PI2>", var2)
            measure = dependency.extra[0]
            val_unit = measure.name.replace('most ', '').strip().split()
            val = val_unit[0]
            unit = val_unit[1]
            template = template.replace('<DISTANCE>', val).replace('<UNIT>', unit)
        return template

    def define_situations(self, dependency):
        # todo
        return

    def construct_where(self):
        where_clause = ''
        # define var_ids for concepts
        where_clause += self.declare()

        criteria = self.dependencies['criteria']
        for criterion in criteria:
            if criterion.relation.link == 'AND/OR':
                continue
            if criterion.relation.name == 'IS/ARE':
                print('todo!')
            elif criterion.relation.link == 'PROPERTY':
                print('todo')
            elif criterion.relation.link == 'NOT':
                print('todo')
            elif criterion.relation.role == 'R':  # spatial relationships
                if len(criterion.extra) == 0:
                    where_clause += self.define_spatial_relationship(criterion)
                else:
                    where_clause += self.define_spatial_relationship(criterion, distance=True)
        # todo define attributes

        # todo define spatial relationships

        # todo situation

        return where_clause

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