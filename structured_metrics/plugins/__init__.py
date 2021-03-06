#!/usr/bin/env python2
import re
"""
Base Plugin class
"""


class Plugin(object):
    target_default = {
        # one or more functions allow you to dynamically configure target properties based on
        # the match object. the target will receive updated fields from the returned dict
        'configure': [lambda self, target: self.default_configure_target(target)],
    }
    priority = 0
    targets_found = 0

    # useful configure functions:
    def default_configure_target(self, target):
        return {}

    def fix_underscores(self, target, keys):
        # SwapCached -> swap_cached
        # keys can be a list of keys or just one key
        try:
            for key in keys:
                target['tags'][key] = self.camel_to_underscore(target['tags'][key])
        except:
            target['tags'][keys] = self.camel_to_underscore(target['tags'][keys])

    def add_tag(self, target, key, val):
        '''
        add tag to existing set of tags
        overiddes any tag with the same name
        '''
        target['tags'][key] = val

    def get_targets(self):
        # "denormalize" dense configuration list into a new list of full-blown configs
        targets = []
        for target in self.targets:
            if 'targets' in target:
                for sub_target in target['targets']:
                    t = target.copy()
                    del t['targets']
                    t.update(sub_target)
                    targets.append(t)
            else:
                targets.append(target)

        for (id, target) in enumerate(targets):
            # merge options into defaults
            # 'configure' is a special case.. we append new entries to the
            # original list.  this allows you to add extra functions, while
            # maintaining the original (which can be overridden).
            # or don't bother with specifying any configure options, and just
            # override the function.
            targets[id] = self.target_default.copy()
            targets[id].update(target)
            targets[id]['configure'] = list(self.target_default['configure'])
            if 'configure' in target:
                if not isinstance(target['configure'], list):
                    target['configure'] = [target['configure']]
                targets[id]['configure'].extend(target['configure'])
            # compile fast match objects
            # because sometimes a target covers multiple metric naming
            # patterns, we must support a list of possible matching regexes.
            # we can't just do '|'.join(list of regexes)
            # because then we can't repeat group names.
            if isinstance(target['match'], basestring):
                target['match'] = [target['match']]
            targets[id]['match_object'] = []
            for regex in target['match']:
                # can raise sre_constants.error ! and maybe other regex errors.
                targets[id]['match_object'].append(re.compile(regex))
            # similar for 'no_match' if specified
            if 'no_match' in target:
                if isinstance(target['no_match'], basestring):
                    target['no_match'] = [target['no_match']]
                targets[id]['no_match_object'] = []
                for regex in target['no_match']:
                    targets[id]['no_match_object'].append(re.compile(regex))
        return targets

    def __init__(self):
        self.targets = self.get_targets()

    # track how many times targets have been yielded, for limit setting
    def reset_target_yield_counters(self):
        for (id, target) in enumerate(self.targets):
            self.targets[id]['yielded'] = 0

    def get_target_id(self, target):
        target_key = ['targets']
        for tag_key in sorted(target['tags'].iterkeys()):  # including the tag key allows to filter out all http things by just writing 'http'
            tag_val = target['tags'][tag_key]
            if tag_val:
                target_key.append('%s:%s' % (tag_key, tag_val))
        return ' '.join(target_key)

    def __create_target(self, match, target_config):
        tags = match.groupdict()
        tags.update({'target_type': target_config['target_type'], 'plugin': self.classname_to_tag()})
        target = {
            'id': match.string,  # graphite metric
            'config': target_config,
            'tags': tags,
        }
        return target

    def __sanitize_target(self, target):
        ret = self.sanitize(target)
        if ret is None:
            return target
        return ret

    def __configure_target(self, target):
        # from dict returned, merge in all keys (not deep. overrides existing
        # keys). you can easily mimic deep merge by just taking original value,
        # merging your stuff in, and returning that, or since modifying the
        # original value directly suffices, just return nothing
        for configure_fn in target['config']['configure']:
            out = configure_fn(self, target)
            if out is not None:
                target.update(out)
        return target

    def sanitize(self, target):
        return None

    def upgrade_metric(self, metric):
        """
        For given proto1 metric, try to upgrade it to proto2 if we can match it to a config
        yield a tuple of id and proto2 metric, being:
            {
                'id': '<..>',  # the exact graphite metric id
                'tags': { tag_key: tag_value [,...]}
            }
        }
        """
        # for every target config, see if the metric meets all criteria
        for (id, target) in enumerate(self.targets):
            if 'limit' in target and target['limit'] == target['yielded']:
                continue
            # metric must not match any of the no_match objects
            yield_metric = True
            for no_match_object in target.get('no_match_object', []):
                no_match = no_match_object.search(metric)
                if no_match is not None:
                    yield_metric = False
                    break
            if not yield_metric:
                continue
            # first match object that creates a match is a winner, yield it
            for match_object in target['match_object']:
                match = match_object.search(metric)
                if match is not None:
                    target = self.__create_target(match, target)
                    target = self.__sanitize_target(target)
                    target = self.__configure_target(target)
                    del target['config']  # not needed beyond this point
                    self.targets_found += 1
                    self.targets[id]['yielded'] += 1
                    return (self.get_target_id(target), target)
                    continue
        return None

    def classname_to_tag(self):
        '''
        FooBarHTTPPlugin -> foo_bar_http
        '''
        name = self.__class__.__name__.replace('Plugin', '')
        return self.camel_to_underscore(name)

    def camel_to_underscore(self, name):
        '''
        from http://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-camel-case/1176023#1176023
        '''
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


    # experimental shortcut functions to easily define targets.
    # some of these would be better provided by the plugins themselves
    @staticmethod
    def gauge(match):
        return {
            'match': match,
            'target_type': 'gauge'
        }

    @staticmethod
    def count(match):
        return {
            'match': match,
            'target_type': 'count'
        }

    @staticmethod
    def rate(match):
        return {
            'match': match,
            'target_type': 'rate'
        }

    @staticmethod
    def counter(match):
        return {
            'match': match,
            'target_type': 'counter'
        }

    @staticmethod
    def statsd_gauge(match):
        return {
            'match': '^stats.gauges\.%s' % match,
            'target_type': 'gauge'
        }

    @staticmethod
    def statsd_count(match):
        return {
            'match': '^stats_counts\.%s' % match,
            'target_type': 'count'
        }

    @staticmethod
    def statsd_rate(match):
        return {
            'match': '^stats\.%s' % match,
            'target_type': 'rate'
        }

# vim: ts=4 et sw=4:
