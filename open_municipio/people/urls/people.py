from django.conf.urls.defaults import *
from open_municipio.people.views import PoliticianDetailView, PoliticianListView


urlpatterns = patterns('',
    url(r'^$', PoliticianListView.as_view(), name='om_politician_list'),
    url(r'^(?P<slug>[-\w]+)/$', PoliticianDetailView.as_view(), name='om_politician_detail')
)
    