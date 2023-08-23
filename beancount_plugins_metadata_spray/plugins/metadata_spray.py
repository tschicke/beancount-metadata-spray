# metadata_spray.py

import collections
import re
from decimal import Decimal

from beancount.core import data
from beancount.core import account
from beancount.core import getters
from beancount.core.data import Custom

__plugins__ = ('metadata_spray_entries',)

MetadataSprayError = collections.namedtuple(
    'MetadataSprayError', 'source message entry')

# Metadata Replace Types
# ---
# This dictates how the metadata spray will deal with situations
# where a type of metadata already exists.
# Generally the default is to return an error,
# but the options to either not overwrite metadata or
# replace all also exist.
MetadataSprayReplaceType = ['return_error', 'dont_overwrite', 'overwrite']

metadata_spray_error_meta = data.new_metadata('<metadata_spray>', 0)


def metadata_spray(entry,
                   replace_type,
                   metadata_dict):
    errors = []
    entry_meta = entry.meta

    for metadata_key in metadata_dict:
        if metadata_key in entry_meta:
            if replace_type == 'return_error':
                error_meta = data.new_metadata(
                    '<metadata_spray>', entry.meta['lineno'])
                errors.append(
                    MetadataSprayError(
                        error_meta,
                        "Existing metadata \'{}\' found in {} \'{}\', skipping".format(
                            metadata_key, entry.__class__.__name__, entry.name), None))
                continue
            elif replace_type == 'dont_overwrite':
                continue

        entry_meta[metadata_key] = metadata_dict[metadata_key]

    return errors


def spray_open(entry, config):
    errors = []
    if not 'regex' in config:
        pattern = config['pattern']
        config['regex'] = re.compile(pattern)
    regexer = config['regex']

    if not regexer.match(entry.account):
        return errors
    return metadata_spray(
        entry,
        config['replace_type'],
        config['metadata_dict'])


def spray_commodity(entry, config):
    errors = []
    pattern = config['pattern']
    if not 'regex' in config:
        config['regex'] = re.compile(pattern)
    regexer = config['regex']

    if not regexer.match(entry.currency):
        #print(f'Not spraying {pattern}: {entry.currency}')
        return errors
    #print(f'Spraying {pattern}: {entry.currency} with {config["metadata_dict"]}')
    return metadata_spray(
        entry,
        config['replace_type'],
        config['metadata_dict'])


# Supported spray types
MetadataSprayHandlers = {
    'open': spray_open,
    'commodity': spray_commodity,
}

def metadata_spray_entries(entries, options_map, config_str):
    """
    Insert metadata on
    """
    errors = []

    config_obj = eval(config_str, {'Decimal': Decimal}, {})
    sprays = config_obj['sprays']
    spray_dict = {}
    for spray in sprays:

        if ('spray_type' not in spray) or \
                ('replace_type' not in spray):
            errors.append(
                MetadataSprayError(metadata_spray_error_meta,
                                   "Missing spray or replace type, \
                    skipping this spray operation",
                                   None)
            )
            continue

        spray_type = spray['spray_type']
        if spray_type not in MetadataSprayHandlers:
            errors.append(
                MetadataSprayError(metadata_spray_error_meta,
                                   "Invalid spray type: {} \
                                skipping this spray operation".format(
                                       spray_type),
                                   None))
            continue

        replace_type = spray['replace_type']
        if(replace_type not in MetadataSprayReplaceType):
            errors.append(
                MetadataSprayError(metadata_spray_error_meta,
                                   "Invalid spray type: {} \
                                skipping this spray operation".format(
                                       spray_type),
                                   None))
            continue

        if spray_type not in spray_dict:
            spray_dict[spray_type] = []

        spray_dict[spray_type].append(spray)

    for entry in entries:
        spray_type = entry.__class__.__name__.lower()
        sprays = spray_dict.get(spray_type, None)
        if sprays is None:
            continue

        for spray in sprays:
            errors += MetadataSprayHandlers[spray_type](entry, spray)

    return entries, errors
