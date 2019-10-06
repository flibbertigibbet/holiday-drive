from holiday.visitor_views import *
from holiday.views import *
from django.conf.urls import patterns, include, url
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
                       # Examples:
                       # url(r'^$', 'holiday.views.home', name='home'),
                       # url(r'^blog/', include('blog.urls')),

                       ### FETCH URLS (return json) ###
                       # http://localhost:8000/fetch/searchkids/Z/Z/Z/Z/1
                       url(r'^fetch/searchkids/(?P<gender>[MFZ])/(?P<program_type>[\dZ]+)' + \
                           r'/(?P<age_range>[0-4Z])/(?P<urgent_need>[TFZ])/(?P<page>\d+)',
                           children_results),

                       url(r'^fetch/searchfamilies/(?P<program_type>[\dZ]+)/(?P<family_size>[2-5Z])' + \
                           r'/(?P<urgent_need>[TFZ])/(?P<page>\d+)', families_results),

                       url(
                           r'^fetch/searchgeneral/(?P<item_category>[\dZ]+)/(?P<page>\d+)', general_results),

                       url(
                           r'^fetch/searchprograms/(?P<program_type>[\dZ]+)/(?P<page>\d+)', programs_results),

                       # for staff - login required
                       url(r'^fetch/staff/children/(?P<family_id>[\dZ]+)/(?P<approved>[TFZ])/(?P<child_name>\w*)/(?P<page>\d+)',
                           staff_fetchkids),

                       url(r'^fetch/staff/families/(?P<approved>[TFZ])/(?P<page>\d+)',
                           staff_fetchfamilies),

                       ### VISITOR URLS ###
                       url(r'^thanks/$', thanks),

                       # url(r'^email/$', test_email), # for testing html email

                       url(r'^$', holiday_drive),  # put visitor site at root

                       url(r'^search_children/$', search_children),

                       url(r'^search_families/$', search_families),

                       url(r'^search_general/$', search_general),

                       url(r'^search_programs/$', search_programs),

                       url(r'^sponsorprogram/(?P<program_id>\d*)', sponsor_program),

                       url(r'^sponsorchild/(?P<child_id>\d*)', sponsor_child),

                       url(r'^sponsorfamily/(?P<family_id>\d*)', sponsor_family),

                       url(r'^sponsorgeneral/(?P<item_id>\d*)/(?P<qty>\d*)',
                           sponsor_general),

                       ####################

                       ### STAFF URLS ###
                       url(r'^addchildcheck/$', add_child_check),

                       # url(r'^addchild/', no_new_kids), # uncomment when done for the year

                       # comment out when done for the year
                       url(r'^addchild/',
                           login_required(ChildWizard.as_view(
                               CHILD_FORMS).__call__),
                           name='ChildWizard'),

                       url(r'^editchild/(?P<child_id>\d*)',
                           login_required(ChildWizard.as_view(
                               CHILD_FORMS).__call__),
                           name='ChildWizard'),
                       #############

                       # uncomment when done for the year
                       # url(r'^addfamily/(?P<family_id>\d*)', no_new_kids),

                       # comment out when done for the year
                       url(r'^addfamily/(?P<family_id>\d*)',
                           login_required(FamilyWizard.as_view(CHILD_FORMS).__call__), name='FamilyWizard'),
                       ###############

                       # to support filtering drop-downs for wishlist items based on category
                       url(r'^select_filter/', include('smart_selects.urls')),

                       # TODO: should this be removed? looks like no-new-kids redirect is in view
                       # url(r'^add_new_family/$', no_new_kids),  # uncomment when done for the year

                       url(r'^add_new_family/$', add_new_family),

                       url(r'^view_families/$', view_families),
                       url(r'^view_families/(?P<approved>[TF])/$',
                           view_families),

                       url(r'^view_children/$', view_children),
                       url(r'^view_children/(?P<family_id>\d*)/$', view_children),
                       url(
                           r'^view_children/(?P<family_id>[\dZ]+)/(?P<approved>[TF])/$', view_children),

                       url(r'^staff_start/$', programstaff_start),

                       # uncomment when done for the year
                       # url(r'^add_another_child_to_family/(?P<family_id>\d+)/$', no_new_kids),

                       # comment out when done for the year
                       url(r'^add_another_child_to_family/(?P<family_id>\d+)/$',
                           add_another_child_to_family),
                       ###################

                       # Login / logout.
                       (r'^login/$', 'django.contrib.auth.views.login'),

                       (r'^check_first_login/$', 'holiday.views.check_first_login'),

                       (r'^logout/$', 'holiday.views.logout_page'),

                       # password change
                       (r'^password_change_done/$',
                           'django.contrib.auth.views.password_change_done'),

                       (r'^password_change/$',
                           'django.contrib.auth.views.password_change',
                           {'post_change_redirect': '/password_change_done/', 'current_app': 'holiday'}),

                       (r'^program_director_initial/$', program_director_initial),
                       #####################

                       ### ADMIN URLS ###
                       # admin documentation:
                       url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
                       # enable the admin:
                       url(r'^admin/', include(admin.site.urls)),
                       )
