# Copyright (c) Microsoft Corporation
# Licensed under the MIT License.

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from tempfile import TemporaryDirectory
from common_utils import (create_boston_data,
                          create_cancer_data,
                          create_iris_data,
                          create_binary_classification_dataset,
                          create_models_classification,
                          create_models_regression)
from raitools import RAIAnalyzer, ModelTask
from raitools._internal.constants import ManagerNames
from explainer_manager_validator import (setup_explainer,
                                         validate_explainer)
from counterfactual_manager_validator import validate_counterfactual
from error_analysis_validator import (setup_error_analysis,
                                      validate_error_analysis)

LABELS = "labels"
DESIRED_CLASS = 'desired_class'
DESIRED_RANGE = 'desired_range'


class TestRAIAnalyzer(object):

    @pytest.mark.parametrize('manager_type', [ManagerNames.ERROR_ANALYSIS,
                                              ManagerNames.COUNTERFACTUAL,
                                              ManagerNames.EXPLAINER])
    def test_rai_analyzer_iris(self, manager_type):
        x_train, x_test, y_train, y_test, feature_names, classes = \
            create_iris_data()
        x_train = pd.DataFrame(x_train, columns=feature_names)
        x_test = pd.DataFrame(x_test, columns=feature_names)
        models = create_models_classification(x_train, y_train)
        x_train[LABELS] = y_train
        x_test[LABELS] = y_test
        manager_args = {DESIRED_CLASS: 0}

        for model in models:
            run_rai_analyzer(model, x_train, x_test, LABELS,
                             manager_type, manager_args, classes)

    @pytest.mark.parametrize('manager_type', [ManagerNames.ERROR_ANALYSIS,
                                              ManagerNames.COUNTERFACTUAL,
                                              ManagerNames.EXPLAINER])
    def test_rai_analyzer_cancer(self, manager_type):
        x_train, x_test, y_train, y_test, feature_names, classes = \
            create_cancer_data()
        x_train = pd.DataFrame(x_train, columns=feature_names)
        x_test = pd.DataFrame(x_test, columns=feature_names)
        models = create_models_classification(x_train, y_train)
        x_train[LABELS] = y_train
        x_test[LABELS] = y_test
        manager_args = {DESIRED_CLASS: 'opposite'}

        for model in models:
            run_rai_analyzer(model, x_train, x_test, LABELS,
                             manager_type, manager_args, classes)

    @pytest.mark.parametrize('manager_type', [ManagerNames.ERROR_ANALYSIS,
                                              ManagerNames.EXPLAINER])
    def test_rai_analyzer_binary(self, manager_type):
        x_train, y_train, x_test, y_test, classes = \
            create_binary_classification_dataset()
        x_train = pd.DataFrame(x_train)
        x_test = pd.DataFrame(x_test)
        models = create_models_classification(x_train, y_train)
        x_train[LABELS] = y_train
        x_test[LABELS] = y_test
        manager_args = None

        for model in models:
            run_rai_analyzer(model, x_train, x_test, LABELS,
                             manager_type, manager_args,
                             classes=classes)

    @pytest.mark.parametrize('manager_type', [ManagerNames.COUNTERFACTUAL])
    def test_raianalyzer_boston(self, manager_type):
        x_train, x_test, y_train, y_test, feature_names = \
            create_boston_data()
        x_train = pd.DataFrame(x_train, columns=feature_names)
        x_test = pd.DataFrame(x_test, columns=feature_names)
        models = create_models_regression(x_train, y_train)
        x_train[LABELS] = y_train
        x_test[LABELS] = y_test
        manager_args = {DESIRED_RANGE: [10, 20]}

        for model in models:
            run_rai_analyzer(model, x_train, x_test, LABELS,
                             manager_type, manager_args)


def run_rai_analyzer(model, x_train, x_test, target_column,
                     manager_type, manager_args=None, classes=None):
    if classes is not None:
        task_type = ModelTask.CLASSIFICATION
    else:
        task_type = ModelTask.REGRESSION
    if manager_type == ManagerNames.COUNTERFACTUAL:
        x_test = x_test[0:1]
    rai_analyzer = RAIAnalyzer(model, x_train, x_test, target_column,
                               task_type=task_type)
    if manager_type == ManagerNames.EXPLAINER:
        setup_explainer(rai_analyzer)
    if manager_type == ManagerNames.ERROR_ANALYSIS:
        setup_error_analysis(rai_analyzer)
    validate_rai_analyzer(rai_analyzer, x_train, x_test, target_column,
                          task_type)
    if manager_type == ManagerNames.EXPLAINER:
        validate_explainer(rai_analyzer, x_train, x_test, classes)
    if manager_type == ManagerNames.COUNTERFACTUAL:
        desired_range = None
        desired_class = None
        if manager_args is not None:
            if DESIRED_CLASS in manager_args:
                desired_class = manager_args[DESIRED_CLASS]
            if DESIRED_RANGE in manager_args:
                desired_range = manager_args[DESIRED_RANGE]
        validate_counterfactual(rai_analyzer, x_train, target_column,
                                desired_class, desired_range)
    if manager_type == ManagerNames.ERROR_ANALYSIS:
        validate_error_analysis(rai_analyzer)
    with TemporaryDirectory() as tempdir:
        path = Path(tempdir) / 'rai_test_path'
        # save the rai_analyzer
        rai_analyzer.save(path)
        # load the rai_analyzer
        rai_analyzer = RAIAnalyzer.load(path)
        if manager_type == ManagerNames.EXPLAINER:
            setup_explainer(rai_analyzer)
        validate_rai_analyzer(rai_analyzer, x_train, x_test,
                              target_column, task_type)
        if manager_type == ManagerNames.EXPLAINER:
            validate_explainer(rai_analyzer, x_train, x_test, classes)
        if manager_type == ManagerNames.ERROR_ANALYSIS:
            validate_error_analysis(rai_analyzer)


def validate_rai_analyzer(rai_analyzer, x_train, x_test, target_column,
                          task_type):
    pd.testing.assert_frame_equal(rai_analyzer.train, x_train)
    pd.testing.assert_frame_equal(rai_analyzer.test, x_test)
    assert rai_analyzer.target_column == target_column
    assert rai_analyzer.task_type == task_type
    np.testing.assert_array_equal(rai_analyzer._classes,
                                  x_train[target_column].unique())
