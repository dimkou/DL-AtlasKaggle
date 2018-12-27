import numpy as np
import pandas as pd
from data_loader.data_generator import DataGenerator, DataTestLoader
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import MultiLabelBinarizer
from utils.config import process_config
from utils.dirs import create_dirs
from utils.utils import get_args
from models.random_forest import RandomForestBaseline


def get_baseline_CV_score(feats, labels, estimator, scores=['f1_macro']):
    """ Calculate the cross-validation score
    of the baseline estimator

    Args:
        feats: input features to classifiers
        labels: one-hot multilabel representation
        scores: array of scoring function to assess by CV

    Returns:
        cv_scores: an array of scores objects
    """
    cv_scores = []
    for score in scores:
        cv_scores = np.append(
            cv_scores, cross_val_score(
                estimator, feats, labels, scoring=score))
    return cv_scores


def fit_predict(train_feats, train_labels, test_feats, estimator):
    """ Wrapper for the fit + predict pipeline.

    Args:
        train_feats: matrix[n_samples, n_feats] with training features
        train_labels: one-hot multilabel representation [n_samples, n_classes]
        estimator: object derived from Sklearn BaseEstimator

    Note:
        RF estimator can return None as class, don't know how Kaggle
        handles that. TODO: check this case.
    """
    bin = MultiLabelBinarizer(classes=np.arange(28))
    bin.fit(train_labels)  # needed for instantiation of the object
    estimator.fit(train_feats, train_labels)
    one_hot_pred = estimator.predict(test_feats)
    predicted_labels = bin.inverse_transform(one_hot_pred)
    return predicted_labels


def main():
    """ Main procedure: extract features,
    get RF cross-validation performance,
    fit and predict baseline and save csv for Kaggle.

    Note:
        Set the batch_size to some big number ~1000
        for better parmap performance.
    """
    # capture the config path from the run arguments
    # then process the json configuration file
    try:
        args = get_args()
        config = process_config(args.config)

    except Exception:
        print("missing or invalid arguments")
        exit(0)
    # create your data generator
    TrainingSet = DataGenerator(config)
    all_batches = TrainingSet.batch_iterator()

    # init model
    estimator = RandomForestBaseline(
        n_estimators=config.n_estimators,
        n_jobs=-1,
        random_state=42,
        class_weight=config.class_weight)

    # extract features
    train_feats, train_labels = estimator._extract_features(
        all_batches, config.patch_size)
    samples_per_class = np.sum(train_labels, axis=0)
    print("Samples per class: ", samples_per_class.tolist())
    print("Total samples: ", np.sum(train_labels))

    # get cv score
    print("Calculating CV score...")
    cv_scores = get_baseline_CV_score(train_feats, train_labels, estimator)
    print("CV Score:", cv_scores)

    # Load Test Set
    TestSet = DataTestLoader(config)
    test_batches = TestSet.batch_iterator()

    # Fit and predict for Kaggle
    test_feats = estimator._extract_features(
        test_batches, config.patch_size, train=False)
    print("Test dataset shape:", np.shape(test_feats))
    prediction = fit_predict(train_feats, train_labels, test_feats, estimator)
    ids = TestSet.image_ids
    print(np.shape(ids))
    result = pd.DataFrame()

    string_pred = [
        ' '.join([str(p) for p in sample_pred]) for sample_pred in prediction
    ]
    print(np.shape(string_pred))
    result['Id'] = ids
    result['Predict'] = string_pred
    print(result)
    create_dirs([config.summary_dir])
    result.to_csv(config.summary_dir + '/prediction.csv', index=False)


if __name__ == '__main__':
    main()
