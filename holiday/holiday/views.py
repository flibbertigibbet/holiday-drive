import json

from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponse, HttpResponseRedirect
from django.forms.models import inlineformset_factory
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, render_to_response, redirect
from django.template import RequestContext
from django.views.decorators.cache import never_cache

from formtools.wizard.views import SessionWizardView

from holiday.forms import (ChildPage1, ChildWishlistFormSet, DirectorSwitchProgram,
                           InitialProgramDirector, SearchKidName)
from holiday.models import (Child, DirectorMultiPrograms, Family, Program, ProgramStaff,
                            ProgramMaximumChildren, WishlistChild)


# STAFF SITE VIEWS
@login_required
def add_child_check(request):
    # check if we're allowed to add more children for this program
    staff = ProgramStaff.objects.get(user=request.user)
    program_limit = ProgramMaximumChildren.objects.filter(
        program=staff.program)
    if program_limit.exists():
        limit = program_limit.get(program=staff.program).maximum_children
        got_ct = Child.objects.filter(program=staff.program).count()
        if got_ct < limit:
            messages.info(request, staff.program.__unicode__() +
                          " can enter a maximum of " +
                          str(limit) + " children.  Currently there are " + str(got_ct) + ".")
        else:
            # too many, can't add another
            messages.error(request, "Maximum number of children already entered for " +
                           staff.program.__unicode__() + ".")
            return HttpResponseRedirect('/staff_start/')
    return HttpResponseRedirect('/addchild/')


@login_required
def staff_fetchfamilies(request, approved, page=1):
    try:
        myuser = ProgramStaff.objects.get(user=request.user)
        myprogram = myuser.program
        director = request.user.groups.filter(
            name='Program Directors').exists()
        families_data = {'staff_families': {'count': 0, 'last_page': True, 'families': [],
                                            'director': director}}
        data = json.dumps(families_data)
        qry = Family.objects.filter(program=myprogram)
        if approved != 'Z':
            if approved == 'F':
                qry = qry.filter(approved=False)
            else:
                qry = qry.filter(approved=True)
    except ProgramStaff.DoesNotExist:
        # not a staff member? shouldn't happen
        return HttpResponseRedirect('/staff_start/')
    except Family.DoesNotExist:
        # no families in program
        return HttpResponse(data, content_type='application/json')
    qry = qry.prefetch_related('child_set')
    fam_ct = qry.count()
    pag = Paginator(qry, 20, orphans=5)  # 20 results per page; 5 minimum
    try:
        families = pag.page(page)
    except PageNotAnInteger:
        families = pag.page(1)
    except EmptyPage:
        # page number out of range; return nothing
        return HttpResponse(data, content_type='application/json')
    last_page = True
    if families.has_next():
        last_page = False
    fam_list = []
    for fam in families:
        fam_kids = fam.child_set.all()
        if not fam_kids:
            fam_list.append({'id': fam.id, 'approved': fam.approved, 'kid_count': 0,
                             'kids': [], 'can_approve': False})
            continue
        can_approve = True
        kid_list = []
        for kid in fam_kids:
            kid_list.append({'desc': kid.__unicode__(),
                             'approved': kid.approved})
            if not kid.approved:
                can_approve = False  # can only approve family if all kids approved
        fam_list.append({'id': fam.id, 'approved': fam.approved, 'kids': kid_list,
                         'kid_count': fam_kids.count(), 'can_approve': can_approve})
    if families:
        families_data = {'staff_families': {'count': fam_ct, 'last_page': last_page,
                                            'families': fam_list, 'director': director}}
        data = json.dumps(families_data)
    return HttpResponse(data, content_type='application/json')


@login_required
def view_families(request, approved='Z'):
    if request.method == 'POST':
        if 'approve' in request.POST:
            try:
                fam = Family.objects.get(id=request.POST['approve'])
                fam.approved = True
                if not fam.keep_unavailable and not fam.donor_set.count():
                    fam.available_for_sponsorship = True
                fam.save()
                messages.success(request, "Family " +
                                 str(fam.id) + " has been approved")
            except:
                messages.error(request, "Failed to set approval")
        elif 'disapprove' in request.POST:
            try:
                fam = Family.objects.get(id=request.POST['disapprove'])
                fam.approved = False
                if not fam.keep_available:
                    fam.available_for_sponsorship = False
                fam.save()
                messages.success(
                    request, "Approval removed from family " + str(fam.id))
            except:
                messages.error(request, "Failed to set approval")
    try:
        myuser = ProgramStaff.objects.get(user=request.user)
        myprogram = myuser.program
    except:
        # no user/program? shouldn't happen
        return HttpResponseRedirect('/staff_start/')
    json_url = '/fetch/staff/families/' + approved + '/'
    context_data = {'program': myprogram, 'json_url': json_url}
    if approved == 'F':
        context_data['need_approval'] = True
    else:
        context_data['need_approval'] = False
    return render_to_response('view_families.html', context_data,
                              context_instance=RequestContext(request))


@login_required
def staff_fetchkids(request, family_id='Z', approved='Z', child_name='0', page=1):
    qry = data = fam = myprogram = ''
    try:
        myuser = ProgramStaff.objects.get(user=request.user)
        myprogram = myuser.program
        director = request.user.groups.filter(
            name='Program Directors').exists()
        children_data = {'staffkids': {'count': 0, 'last_page': True, 'kids': [],
                                       'director': director}}
        data = json.dumps(children_data)
        qry = Child.objects.filter(program=myprogram)
        if child_name != '0' and len(child_name) > 0:
            qry = qry.filter(first_name__icontains=child_name)
        if approved != 'Z':
            if approved == 'F':
                qry = qry.filter(approved=False)
            else:
                qry = qry.filter(approved=True)
        if family_id != 'Z':
            try:
                fam = Family.objects.get(id=family_id)
            except Family.DoesNotExist:
                # bad family id
                return HttpResponse(data, content_type='application/json')
        # order list of kids by family ID (newest first),
        # then alphabetically by first name
        if fam:
            qry = qry.filter(family=fam).order_by('-family', 'first_name')
        else:
            qry = qry.order_by('-family', 'first_name')
            fam = ''
    except ProgramStaff.DoesNotExist:
        # not a staff member? shouldn't happen
        return HttpResponseRedirect('/staff_start/')
    except Child.DoesNotExist:
        return HttpResponse(data, content_type='application/json')
    kid_list = []
    qry = qry.select_related('clothing_size', 'clothing_size__size_category',
                             'family').prefetch_related('wishlistchild_set',
                                                        'wishlistchild_set__item',
                                                        'wishlistchild_set__category')
    kid_ct = qry.count()
    pag = Paginator(qry, 20, orphans=5)  # 20 results per page; 5 minimum
    try:
        children = pag.page(page)
    except PageNotAnInteger:
        children = pag.page(1)
    except EmptyPage:
        # page number out of range; return nothing
        return HttpResponse(data, content_type='application/json')
    last_page = True
    if children.has_next():
        last_page = False
    for kid in children:
        akid = {'id': kid.id, 'clothing_size': kid.clothing_size.__unicode__(),
                'approved': kid.approved, 'first_name': kid.first_name, 'desc': kid.__unicode__()}
        if kid.family:
            akid['family_id'] = kid.family.id
            akid['family_approved'] = kid.family.approved
        else:
            akid['family_id'] = ''
            akid['family_approved'] = False
        wishlist = kid.wishlistchild_set.all()
        wlist = []
        for wish in wishlist:
            wlist.append({'wish': wish.__unicode__(), 'notes': wish.notes})
        akid['wishlist'] = wlist
        kid_list.append(akid)
    if children:
        children_data = {'staffkids': {'count': kid_ct, 'last_page': last_page,
                                       'kids': kid_list, 'director': director}}
    data = json.dumps(children_data)
    return HttpResponse(data, content_type='application/json')


@login_required
def view_children(request, family_id='Z', approved='Z'):
    child_name = '0'  # search term
    myform = SearchKidName()
    if request.method == 'POST':
        if 'approve' in request.POST:
            try:
                kid = Child.objects.get(id=request.POST['approve'])
                kid.approved = True
                if not kid.keep_unavailable and not kid.donor_set.count():
                    kid.available_for_sponsorship = True
                kid.save()
                messages.success(request, kid.first_name +
                                 "'s record has been approved")
            except:
                messages.error(request, "Failed to set approval")
        elif 'disapprove' in request.POST:
            try:
                kid = Child.objects.get(id=request.POST['disapprove'])
                kid.approved = False
                if not kid.keep_available:
                    kid.available_for_sponsorship = False
                kid.save()
                msg = "Approval removed from " + kid.first_name + "'s record"
                if kid.family:
                    if kid.family.approved:
                        kid.family.approved = False
                        if not kid.family.keep_available:
                            kid.family.available_for_sponsorship = False
                        kid.family.save()
                        msg += " and from family #" + str(kid.family.id) + "."
                messages.success(request, msg)
            except:
                messages.error(request, "Failed to set approval")
        else:
            myform = SearchKidName(request.POST, prefix='search_kid')
            if myform.is_valid():
                child_name = myform.cleaned_data.get('child_name')
                if len(child_name) == 0:
                    child_name = '0'
    else:
        myform = SearchKidName(prefix='search_kid')

    try:
        myuser = ProgramStaff.objects.get(user=request.user)
        myprogram = myuser.program
        program_limit = ProgramMaximumChildren.objects.filter(
            program=myprogram)
        if program_limit.exists():
            limit = program_limit.get(program=myprogram).maximum_children
            messages.info(request, myprogram.__unicode__() + " can enter a maximum of " +
                          str(limit) + " children.")
    except:
        # not a staff account? shouldn't happen
        return HttpResponseRedirect('/staff_start/')
    json_url = '/fetch/staff/children/' + str(family_id) + '/' + approved + '/' + \
        child_name + '/'
    context_data = {'json_url': json_url, 'family': family_id, 'program': myprogram,
                    'form': myform}
    if approved == 'F':
        context_data['need_approval'] = True
    else:
        context_data['need_approval'] = False
    if len(child_name) > 0:
        context_data['child_name'] = child_name
    return render_to_response('view_children.html', context_data,
                              context_instance=RequestContext(request))


# WIZARDS
CHILD_FORMS = [('page1', ChildPage1),
               ('page_wishlist', inlineformset_factory(Child, WishlistChild, extra=3,
                                                       max_num=3, fields='__all__', can_delete=True, formset=ChildWishlistFormSet))]
CHILD_TEMPLATES = {'page1': 'child_page1.html',
                   'page_wishlist': 'child_page_wishlist.html'}


class ChildWizard(SessionWizardView):
    instance = None
    child_id = None

    def get_form_instance(self, step):
        if self.instance is None:
            if 'child_id' in self.kwargs and self.kwargs['child_id']:
                # edit existing; track child_id in session data
                self.storage.data['child_id'] = self.kwargs['child_id']
                # this works for page1, where there's the kwarg
                self.instance = Child.objects.get(id=self.kwargs['child_id'])
            else:
                child_id = self.storage.data.get('child_id', None)
                if child_id:
                    self.instance = Child.objects.get(id=child_id)
                else:
                    # add new
                    print("adding new on step " + step)
                    if step == 'page1':
                        self.instance = Child()
                        # set program staff ID.  Can't do in initial data
                        staff = ProgramStaff.objects.get(
                            user=self.request.user)
                        self.instance.staff_entering = self.request.user
                        # get staff member's progam from ProgramStaff object
                        self.instance.program = staff.program
        return self.instance

    def get_context_data(self, form, **kwargs):
        context = super(ChildWizard, self).get_context_data(
            form=form, **kwargs)
        child_id = self.storage.data.get('child_id', None)
        if child_id:
            context.update(
                {'edit_kid': Child.objects.get(id=child_id).__unicode__})
        else:
            cleaned_data = self.get_cleaned_data_for_step('page1')
            if cleaned_data:
                kid_name = cleaned_data.get('first_name')
                # kid_gender = cleaned_data.get('gender')
                kid_age = cleaned_data.get('age')
                kid_fam = cleaned_data.get('family')
                kidstr = kid_name + ', ' + str(kid_age) + " years old"
                if kid_fam:
                    kidstr += ", in family " + str(kid_fam.id)
                context.update({'add_kid': kidstr})
        return context

    def get_template_names(self):
        return [CHILD_TEMPLATES[self.steps.current]]

    def get_form(self, step=None, data=None, files=None):
        form = super(ChildWizard, self).get_form(step, data, files)
        if step is None:
            step = self.steps.current
        if step == 'page1':
            # filter families by program
            form.fields['family'].queryset = Family.objects.filter(
                program=self.instance.program)
        return form

    @never_cache
    def done(self, form_list, **kwargs):
        # set approved to false for edited items
        self.instance.approved = False
        if not self.instance.keep_available:
            self.instance.available_for_sponsorship = False
        self.instance.save()  # save first, then save m2m data
        # save wishlist data
        child_id = self.storage.data.get('child_id', None)
        wishes_data = self.get_cleaned_data_for_step('page_wishlist') or {}
        for w in wishes_data:
            if child_id and w.get('id'):
                # update existing. 'id' contains full instance of model... hunh?
                wish = w['id']
            else:
                # add new
                wish = WishlistChild(child=self.instance)
            if 'category' in w:
                wish.category = w['category']
            else:
                continue  # no category; skip adding
            if 'item' in w:
                wish.item = w['item']
            if 'have_other' in w:
                wish.have_other = w['have_other']
            else:
                wish.have_other = False
            if 'other_item' in w:
                wish.other_item = w['other_item']
            if 'notes' in w:
                wish.notes = w['notes']

            wish.save()

        # redirect to staff start and show success message
        if child_id:
            messages.success(self.request, "Child has been updated")
        else:
            messages.success(self.request, "Child has been added")
        return HttpResponseRedirect('/staff_start/')


class FamilyWizard(ChildWizard):
    instance = None

    def get_form_instance(self, step):
        if self.instance is None:
            self.instance = Child()
            # set program staff ID.  Can't do in initial data
            staff = ProgramStaff.objects.get(user=self.request.user)
            self.instance.staff_entering = self.request.user
            print(self.instance.staff_entering.id)
            # get staff member's progam from ProgramStaff object
            self.instance.program = staff.program
            if self.kwargs['family_id']:
                print('got family id for instance ' + self.kwargs['family_id'])
                # if adding another kid to family
                self.instance.family = Family.objects.get(
                    id=self.kwargs['family_id'])
        return self.instance

    @never_cache
    def done(self, form_list, **kwargs):
        self.instance.save()  # save first, then save m2m data
        # save wishlist data
        wishes_data = self.get_cleaned_data_for_step('page_wishlist') or {}
        for w in wishes_data:
            wish = WishlistChild(child=self.instance)
            if 'category' in w:
                wish.category = w['category']
            if 'item' in w:
                wish.item = w['item']
            if 'have_other' in w:
                wish.have_other = w['have_other']
            else:
                wish.have_other = False
            if 'other_item' in w:
                wish.other_item = w['other_item']
            if 'notes' in w:
                wish.notes = w['notes']
            wish.save()
        messages.success(self.request, "Child has been added")
        return redirect('/add_another_child_to_family/' + str(self.instance.family.id))


@login_required
def no_new_kids(request):
    return render(request, 'no_new_kids.html')


@login_required
def add_new_family(request):
    # uncomment this when done for the year
    # return redirect(no_new_kids)

    # comment this out when done for the year
    # create new family object to add kids to
    staff = ProgramStaff.objects.get(user=request.user)
    new_family = Family(staff_entering=request.user, program=staff.program)
    new_family.save()
    if new_family.id:
        messages.success(request, "Family " + str(new_family.id) +
                         " created.  Enter only the children in the family " +
                         "(do not include the guardians).")
    else:
        messages.error(request, "Failed to create new family")
    # got family; now go add kids to it
    return redirect('/addfamily/' + str(new_family.id))
    ##########


@login_required
def add_another_child_to_family(request, family_id=None):
    # ask to add another child to family, and if so, restart wizard
    print("family id: " + family_id)
    if request.method == 'POST':
        if 'yes' in request.POST:
            return redirect('/addfamily/' + family_id)  # add another
        elif 'no' in request.POST:
            messages.success(request, 'Family ' +
                             family_id + ' has been added.')
            return redirect(programstaff_start)  # done adding family
    return render(request, 'add_another_to_family.html', {'family_id': family_id})


# authentication
@login_required
def program_director_initial(request):
    if request.method == 'POST':
        form = InitialProgramDirector(request.POST)
        if form.is_valid():
            try:
                director = ProgramStaff.objects.get(user=request.user)
                director.phone_number = request.POST['phone_number']
                director.save()
                request.user.first_name = request.POST['first_name']
                request.user.last_name = request.POST['last_name']
                request.user.first_login = False
                request.user.save()
                # go on to password change screen
                messages.success(
                    request, "User information saved successfully.")
                messages.info(request, "Please note:  Program Directors are " +
                              "responsible for picking up all gifts for clients and " +
                              "should be available to pick up gifts from " +
                              "December 17th to December 19th.")
                messages.info(
                    request, 'Almost done!  Please choose a new password.')
                return redirect('/password_change/')
            except:
                messages.error(request, "Failed to save user information.")
    else:
        form = InitialProgramDirector()
    return render(request, 'director_initial_form.html', {'form': form})


@never_cache
@login_required
def programstaff_start(request):
    # After login, check if this is the first login for user.
    # If so, prompt to change password and note first login complete.
    myuser = ProgramStaff.objects.get(user=request.user)
    myprogram = myuser.program.program_name
    context_vars = {'program': myprogram, 'is_director':
                    request.user.groups.filter(name='Program Directors').exists()}
    dir_multi = DirectorMultiPrograms.objects.filter(director=myuser)
    if dir_multi.exists():
        # current user is the director of multiple programs
        if request.method == 'POST':
            try:
                myuser.program = Program.objects.get(
                    id=request.POST['programs'])
                myuser.save()
                myprogram = myuser.program.program_name
                messages.success(request, 'Now managing ' + myprogram + '.')
                context_vars['program'] = myprogram
            except:
                messages.error(request, 'Failed to switch program.')
        d = dir_multi.get(director=myuser)
        form = DirectorSwitchProgram(director=d.id)
        context_vars['form'] = form
    if not request.session.get('checked_first'):
        request.session['checked_first'] = "yes"
        if myuser.first_login:
            if request.user.groups.filter(name='Program Directors').exists():
                # program directors need to give more information, too
                return redirect(program_director_initial)
            myuser.first_login = False
            myuser.save()
            messages.info(request, 'Welcome to the Holiday Drive staff site!  ' +
                          'Please choose a new password.')
            return redirect('/password_change/')
    # not first login
    # RequestContext to get user for menu bar
    return render_to_response('programstaff_start.html',
                              context_vars, context_instance=RequestContext(request))


@never_cache
@login_required
def check_first_login(request):
    # After login, check if this is the first login for user.
    # If so, prompt to change password and note first login complete.
    myuser = ProgramStaff.objects.get(user=request.user)
    if myuser.first_login:
        myuser.first_login = False
        myuser.save()
        request.session['checked_first'] = "yes"  # note we've done check
        messages.info(request, 'Welcome to the Holiday Drive staff site!\n' +
                      'Please choose a new password.')
        return redirect('/password_change/')
    # not first login
    return redirect(programstaff_start)


@never_cache
def logout_page(request):
    # Log users out and re-direct them to the main page.
    logout(request)
    request.session.flush()
    request.session.clear_expired()
    return redirect(programstaff_start)
