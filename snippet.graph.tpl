%graph_id = graph_key.replace('.','').replace('-','_').replace(' ','_') # disallowed in var names
%if 'constants' in graph_data:
%    graph_name_constants = ' '.join(graph_data['constants'].values())
%    graph_name_promoted_constants = ' '.join(graph_data['promoted_constants'].values())
%    graph_name = '<b>%s</b> %s' % (graph_name_constants, graph_name_promoted_constants)
%else:
%    graph_name = graph_key
%end
% for (i, target) in enumerate(graph_data['targets']):
%     if 'name' not in target and 'variables' in target:
%         graph_data['targets'][i]['name'] = ' '.join(target['variables'].values())
%     end
% end
<h2>{{!graph_name}}</h2>
%try: import json
%except ImportError: import simplejson as json
        <div class="chart_container flot" id="chart_container_flot_{{graph_id}}">
            <div class="chart" id="chart_flot_{{graph_id}}" height="300px" width="700px"></div>
            <div class="legend" id="legend_flot_{{graph_id}}"></div>
            <form class="toggler" id="line_stack_form_flot_{{graph_id}}"></form>
        </div>
        <script language="javascript">
	    $(document).ready(function () {
		var graph_data = {{!json.dumps(graph_data)}};
		var defaults = {
		    graphite_url: "{{config.graphite_url}}/render/",
            % if config.anthracite_url is not None:
		    anthracite_url: "{{config.anthracite_url}}",
            % end
		    from: "-24hours",
		    until: "now",
		    height: "300",
		    width: "740",
		    line_stack_toggle: 'line_stack_form_flot_{{graph_id}}',
		    series: {stack: true, lines: { show: true, lineWidth: 0, fill: true }},
		    xaxis: { mode: "time" },
		    legend: { container: '#legend_flot_{{graph_id}}', noColumns: 1 },
		};
		var graph_flot_{{graph_id}} = $.extend({}, defaults, graph_data);
	        $("#chart_flot_{{graph_id}}").graphiteFlot(graph_flot_{{graph_id}}, function(err) { console.log(err); });
	});
        </script>
