############################################################################
# Copyright (c) 2015-2016 Saint Petersburg State University
# Copyright (c) 2011-2015 Saint Petersburg Academic University
# All Rights Reserved
# See file LICENSE for details.
############################################################################


import os
import plotter
import qconfig
from quast_libs.ca_utils.misc import print_file
from quast_libs.log import get_logger
import reporting
logger = get_logger(qconfig.LOGGER_META_NAME)


def get_results_for_metric(ref_names, metric, contigs_num, labels, output_dirpath, report_fname):
    all_rows = []
    cur_ref_names = []
    row = {'metricName': 'References', 'values': cur_ref_names}
    all_rows.append(row)
    results = []
    for i in range(contigs_num):
        row = {'metricName': labels[i], 'values': []}
        all_rows.append(row)
    for i, ref_name in enumerate(ref_names):
        results_fpath = os.path.join(output_dirpath, ref_name, report_fname)
        if not os.path.exists(results_fpath):
            all_rows[0]['values'] = cur_ref_names
            continue
        results_file = open(results_fpath, 'r')
        columns = map(lambda s: s.strip(), results_file.readline().split('\t'))
        if metric not in columns:
            all_rows[0]['values'] = cur_ref_names
            continue
        results.append([])
        cur_ref_names.append(ref_name)
        next_values = map(lambda s: s.strip(), results_file.readline().split('\t'))
        cur_results = [None] * len(labels)
        for j in range(contigs_num):
            values = next_values
            if values[0]:
                metr_res = values[columns.index(metric)].split()[0]
                next_values = map(lambda s: s.strip(), results_file.readline().split('\t'))
                index_contig = labels.index(values[0])
                cur_results[index_contig] = metr_res
        for j in range(contigs_num):
            all_rows[j + 1]['values'].append(cur_results[j])
            results[-1].append(cur_results[j])
    if not cur_ref_names:
        cur_ref_names = ref_names
    return results, all_rows, cur_ref_names


def get_labels(combined_output_dirpath, report_fname):
    results_fpath = os.path.join(combined_output_dirpath, report_fname)
    results_file = open(results_fpath, 'r')
    values = map(lambda s: s.strip(), results_file.readline().split('\t'))
    return values[1:]


def do(html_fpath, output_dirpath, combined_output_dirpath, output_dirpath_per_ref, metrics, misassembl_metrics, ref_names):
    labels = get_labels(combined_output_dirpath, qconfig.report_prefix + '.tsv')
    contigs_num = len(labels)
    plots_dirname = qconfig.plot_extension.upper()
    for ext in ['TXT', plots_dirname, 'TEX', 'TSV']:
        if not os.path.isdir(os.path.join(output_dirpath, ext)):
            os.mkdir(os.path.join(output_dirpath, ext))
    for metric in metrics:
        if not isinstance(metric, tuple):
            summary_txt_fpath = os.path.join(output_dirpath, 'TXT', metric.replace(' ', '_') + '.txt')
            summary_tex_fpath = os.path.join(output_dirpath, 'TEX', metric.replace(' ', '_') + '.tex')
            summary_tsv_fpath = os.path.join(output_dirpath, 'TSV', metric.replace(' ', '_') + '.tsv')
            summary_png_fpath = os.path.join(output_dirpath, plots_dirname, metric.replace(' ', '_') + '.' + qconfig.plot_extension)
            results, all_rows, cur_ref_names = get_results_for_metric(ref_names, metric, contigs_num, labels, output_dirpath_per_ref, qconfig.transposed_report_prefix + '.tsv')
            if not results or not results[0]:
                continue
            if cur_ref_names:
                transposed_table = [{'metricName': 'Assemblies',
                                    'values': [all_rows[i]['metricName'] for i in xrange(1, len(all_rows))],}]
                for i in range(len(all_rows[0]['values'])):
                    values = []
                    for j in range(1, len(all_rows)):
                        values.append(all_rows[j]['values'][i])
                    transposed_table.append({'metricName': all_rows[0]['values'][i], # name of reference
                                             'values': values})

                print_file(transposed_table, summary_txt_fpath)
                reporting.save_tsv(summary_tsv_fpath, transposed_table)
                reporting.save_tex(summary_tex_fpath, transposed_table)
                reverse = False
                if reporting.get_quality(metric) == reporting.Fields.Quality.MORE_IS_BETTER:
                    reverse = True
                y_label = None
                if metric == reporting.Fields.TOTALLEN:
                    y_label = 'Total length '
                elif metric == reporting.Fields.TOTAL_ALIGNED_LEN:
                    y_label = 'Aligned length '
                elif metric in [reporting.Fields.LARGCONTIG, reporting.Fields.N50, reporting.Fields.NGA50,
                                reporting.Fields.MIS_EXTENSIVE_BASES]:
                    y_label = 'Contig length '
                elif metric == reporting.Fields.LARGALIGN:
                    y_label = 'Alignment length '
                plotter.draw_meta_summary_plot(html_fpath, output_dirpath, labels, cur_ref_names, all_rows, results,
                                               summary_png_fpath, title=metric, reverse=reverse, yaxis_title=y_label)
                if metric == reporting.Fields.MISASSEMBL:
                    mis_results = []
                    report_fname = os.path.join('contigs_reports', qconfig.transposed_report_prefix + '_misassemblies' + '.tsv')
                    if ref_names[-1] == qconfig.not_aligned_name:
                        cur_ref_names = ref_names[:-1]
                    for misassembl_metric in misassembl_metrics:
                        results, all_rows, cur_ref_names = get_results_for_metric(cur_ref_names, misassembl_metric[len(reporting.Fields.TAB):], contigs_num, labels, output_dirpath_per_ref, report_fname)
                        if results:
                            mis_results.append(results)
                    if mis_results:
                        json_points = []
                        for contig_num in range(contigs_num):
                            plot_fpath = os.path.join(output_dirpath, plots_dirname, labels[contig_num] + '_misassemblies')
                            json_points.append(plotter.draw_meta_summary_misassembl_plot(mis_results, cur_ref_names,
                                                                                         contig_num, plot_fpath,
                                                                                         title=labels[contig_num]))
                        if qconfig.html_report:
                            from quast_libs.html_saver import html_saver
                            if ref_names[-1] == qconfig.not_aligned_name:
                                cur_ref_names = ref_names[:-1]
                            if json_points:
                                html_saver.save_meta_misassemblies(html_fpath, output_dirpath, json_points, labels, cur_ref_names)
    logger.main_info('')
    logger.main_info('  Text versions of reports and plots for each metric (for all references and assemblies) are saved to ' + output_dirpath + '/')

