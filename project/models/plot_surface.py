import argparse
import os
from os.path import join
from os import getenv
import sys

import joblib
import pandas as pd
import matplotlib.pyplot as plt
import tkinter
import matplotlib
matplotlib.use('TkAgg')

sys.path.append('.')

from project.models.details import get_model_filepath, ModelDetails, get_model_name
from project.models.scale import init_scale, transform_x, transform_y, inverse_transform_y
from project.utils.app_ids import app_name_to_id
from project.utils.logger import logger
from project.definitions import ROOT_DIR
from project.models.data import (
    get_data_frame,
    get_training_test_split,
    DataFrameColumns,
)

parser = argparse.ArgumentParser(description='Model training and validation.')
parser.add_argument('--app_name', required=True, type=str, help='app name')
parser.add_argument('--alg', required=True, type=str, help='algorithm')
parser.add_argument('--frac', required=False, default=1.0, type=float, help='number of fractions')
parser.add_argument('--scale', action=argparse.BooleanOptionalAction, help='scale the data before learning')
parser.add_argument('--reduced', action=argparse.BooleanOptionalAction,
                    help='use only "CPUs" and "OVERALL_SIZE" features')

if __name__ == "__main__":
    args = parser.parse_args()
    logger.info(args)
    app_id = app_name_to_id.get(args.app_name, None)

    if app_id is None:
        raise ValueError(f'missing app "{args.app_name}" from app map={str(app_name_to_id)}')

    results_filepath = join(ROOT_DIR, '..', 'execution_results/results.csv')
    df, df_err = get_data_frame(results_filepath, app_id)

    if df_err is not None:
        raise ValueError(f'data frame load err: {str(df_err)}')

    columns = None

    if args.reduced:
        columns = [DataFrameColumns.CPUS, DataFrameColumns.OVERALL_SIZE]

    x, y, _, _, _, _ = get_training_test_split(df, 1.0, columns)

    if args.scale:
        init_scale(x, y)

    x_scaled = transform_x(x)
    y_scaled = transform_y(y)

    x_scatter = x[DataFrameColumns.OVERALL_SIZE]
    y_scatter = x[DataFrameColumns.CPUS]
    z_scatter = y[DataFrameColumns.EXECUTION_TIME]
    # plot data points
    ax = plt.axes(projection='3d')
    ax.set_xlabel('total size [B]')
    ax.set_ylabel('mCPUSs')
    ax.set_zlabel('time [s]')
    ax.dist = 8
    ax.scatter(x_scatter, y_scatter, z_scatter, c='#cc0000', alpha=1, label='training points')
    # Load model
    model_details = ModelDetails(args.app_name, args.frac, args.scale, args.reduced)
    model_filepath, err = get_model_filepath(args.alg, model_details)

    if err is not None:
        raise ValueError(err)

    model = joblib.load(model_filepath)
    z_svr = model.predict(x_scaled)
    # ML end
    z_svr_inverse = inverse_transform_y(z_svr)
    z_origin_list = list(z_scatter)
    errors_rel = []
    errors = []

    for index, z_pred in enumerate(z_svr_inverse):
        z_pred = z_pred if z_pred > 0 else min(z_origin_list)
        z_origin = z_origin_list[index]
        error = abs(z_pred - z_origin)
        errors.append(error)
        error_rel = error * 100.0 / z_origin
        errors_rel.append(error_rel)

        if getenv("DEBUG") == "true":
            logger.info('pred: %s' % z_pred)
            logger.info('origin: %s' % z_origin)
            logger.info('error [s] = %s' % error)
            logger.info('error relative [percentage] = %s' % error_rel)

    logger.info('############### SUMMARY ##################')
    logger.info('set length: %s' % len(x))
    logger.info('avg time [s] = %s' % str(sum(z_origin_list) / len(z_origin_list)))
    logger.info('avg error [s] = %s' % str(sum(errors) / len(errors)))
    logger.info('avg error relative [percentage] = %s' % str(sum(errors_rel) / len(errors_rel)))
    # Plot prediction surface
    z_svr_inverse = inverse_transform_y(z_svr)
    x_plot = x[DataFrameColumns.OVERALL_SIZE].to_numpy()
    y_plot = x[DataFrameColumns.CPUS].to_numpy()
    ax.plot_trisurf(x_plot, y_plot, z_svr_inverse, alpha=0.5)
    plt.margins()
    plt.gcf().autofmt_xdate()
    ax.legend()
    plt.title(f'Regression surface ({str(args.alg).upper()}, {args.app_name})')
    plt.show()
