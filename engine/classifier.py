""" A naive bayesian classifier implementation that provides a general purpose,
yet flexible method of classifying objects into classes. """

from db import serializer
import json


class Type(serializer.Serializable):
    """ Calculates the probability that an object belongs to a given class. """

    def __init__(self, cls, class_probability, property_probability=None):
        self.cls = cls
        self.class_probability = class_probability
        self.property_probability = property_probability or {}

    def train(self, dataset):
        """ Train the type classifier from a dataset. """
        data_size = len(dataset)
        for point in dataset:
            for prop in point:
                if prop in self.property_probability:
                    self.property_probability[prop] += 1
                else:
                    self.property_probability[prop] = 1
        for prop, prob in self.property_probability.items():
            self.property_probability[prop] /= data_size

    def as_json(self):
        ''' Return a json friendly representation of Type class. '''
        return {'__type__': True,
                'class': self.cls,
                'class_probability': self.class_probability,
                'properties': self.property_probability}

    def summarize(self):
        """ Return probabilities of both classes and properties. """
        return (self.class_probability, self.property_probability)

    def probability(self, properties):
        """ Return the classification of an object given it's properties. """
        probability = self.class_probability
        for prop in properties:
            probability *= self.property_probability.get(prop, 0)
        return probability

    def __repr__(self):
        return f'Type({self.cls}, {self.property_probability})'


def as_classifier(dct):
    ''' Special object hooks to deserialize classifier json objects '''
    if '__classifier__' in dct:
        return dct['classes']
    elif '__type__' in dct:
        properties = {k: float(v) for k, v in dct['properties'].items()}
        return (dct['class'], dct['class_probability'], properties)
    return dct


class Classifier(serializer.Serializable):
    """ General purpose bayesian classifier. """

    def __init__(self, classes=None):
        ''' Initialize Classifier. '''
        self.classes = classes or []
        serialize_table = {
            'data': 'json_rep'
        }
        super().__init__(serialize_table)

    def train(self, dataset):
        """ Train the classifier from a dataset. """
        items = dataset.items()
        dataset_length = sum([len(v) for _, v in items])
        for cls, points in items:
            cls_type = Type(cls, len(points) / dataset_length)
            cls_type.train(points)
            self.classes.append(cls_type)

    @property
    def json_rep(self):
        ''' Return the classifier as in a json friendly format. '''
        return json.dumps(self, cls=ClassifierEncoder)

    @json_rep.setter
    def json_rep(self, json_string):
        ''' Update the state of the classifier using a json string. '''
        class_array = json.loads(json_string, object_hook=as_classifier)
        types = [Type(cls, cls_prob, property_probability=props) for cls, cls_prob, props in class_array]
        self.classes = types

    def as_json(self):
        ''' Return a json friendly representation of Classifier'''
        return {'__classifier__': True, 'classes': self.classes}

    def classify(self, properties, assumptions={}):
        """ Classify an object into a class. """
        likely_cls = (0, None)
        for cls in self.classes:
            prob = cls.probability(properties)
            prob *= assumptions.get(cls, 1)
            (max_prob, _) = likely_cls
            if prob > max_prob:
                likely_cls = (prob, cls.cls)
        return likely_cls

    def __repr__(self):
        return f'Classifier({self.classes})'


class ClassifierEncoder(json.JSONEncoder):
    ''' Encode Classifier and Properties to json format for database
    insertion. '''
    def default(self, obj):
        ''' Default encoding function. '''
        if isinstance(obj, Classifier) or isinstance(obj, Type):
            return obj.as_json()


def group_by_class(dataset, cls_func=lambda x: (x[0], x[1:])):
    """ Group a list by it's class (or rather by function). e.g
    group_by_class(lambda x: (x[0], x[1:]), [[1, 2, 3], [1, 3, 4]])
    -> {1: [[2, 3], [3, 4]]} """
    classes = {}
    for point in dataset:
        cls, props = cls_func(point)
        if cls in classes:
            classes[cls].append(props)
        else:
            classes[cls] = [props]
    return classes
