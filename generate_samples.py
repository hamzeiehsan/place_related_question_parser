import csv
import json
import logging
from random import sample


def read_file(address):
    if address:
        with open(address, 'r') as f:
            return json.load(f)


def sample_dataset(address, name_dataset):
    dataset = read_file(address)
    sample_dataset = sample(dataset, 100)
    sample_dict = {'Third': {}, 'First': {}, 'Fourth': {}, 'Second': {}}
    sample_dict['Third'][name_dataset] = sample_dataset[:25]
    sample_dict['First'][name_dataset] = sample_dataset[:25]
    sample_dict['Third'][name_dataset].extend(sample_dataset[25:50])
    sample_dict['Second'][name_dataset] = sample_dataset[25:50]
    sample_dict['First'][name_dataset].extend(sample_dataset[75:])
    sample_dict['Fourth'][name_dataset] = sample_dataset[75:]
    sample_dict['Second'][name_dataset].extend(sample_dataset[50:75])
    sample_dict['Fourth'][name_dataset].extend(sample_dataset[50:75])
    return sample_dict


def merge(dataset1, dataset2, dataset3):
    dataset = dataset1
    for k, v in dataset2.items():
        source_name = list(v.keys())[0]
        dataset[k][source_name] = dataset2[k][source_name]
    for k, v in dataset3.items():
        source_name = list(v.keys())[0]
        dataset[k][source_name] = dataset3[k][source_name]
    return dataset


geoqa_samples = sample_dataset('parsing_results/GeoQuestion201.json', 'GEOQA')
simon_samples = sample_dataset('parsing_results/GeoAnQu.json', 'GEOANALYTICAL')
msmarco_samples = sample_dataset('parsing_results/MS MARCO.json', 'MSMARCO')
samples = merge(geoqa_samples, simon_samples, msmarco_samples)
with open('evaluation/samples.json', 'w') as outfile:
    json.dump(samples, outfile)
for person_name, dict in samples.items():
    lines = []
    line = ['name', 'source', 'question', 'where', 'what', 'which', 'how', 'how_adj', 'why', 'place_names',
            'place_types', 'objects', 'qualities', 'object_qualities', 'activities', 'situations',
            'spatial_relationships']
    lines.append(line)
    for source, records in dict.items():
        for record in records:
            if isinstance(record, list):
                logging.info('wait here...')
            line = [person_name, source, record['question']]
            lines.append(line)
    with open('evaluation/{}-sample.csv'.format(person_name), 'w') as writeFile:
        writer = csv.writer(writeFile)
        writer.writerows(lines)
