import json

from django.contrib import messages
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.views.decorators.cache import never_cache

from holiday.forms import (DonorItemsForm, SponsorInformation,
                           SearchPrograms, SearchChildren, SearchFamilies, SearchGeneral)
from holiday.models import (Child, Donor, DonorGeneralWishlist, Family, GeneralWishlistItem,
                            Program, WishlistChild)

# import logging
# l = logging.getLogger('django.db.backends')
# l.setLevel(logging.DEBUG)
# l.addHandler(logging.StreamHandler())


# site-specific settings passed to visitor templates
ORGANIZATION_CONTEXT = {
    'org_name': settings.ORGANIZATION_NAME,
    'site_name': settings.SITE_NAME,
    'cash_donation_link': settings.ORGANIZATION_CASH_DONATION_LINK,
    'main_site': settings.ORGANIZATION_MAIN_SITE,
    'donation_dropoff_locations': settings.DONATION_DROPOFF_LOCATIONS,
    'dropoff_final_date': settings.DONATION_DROPOFF_FINAL_DATE,
    'donor_contact_email': settings.DONOR_CONTACT_EMAIL,
    'twitter': settings.ORGANIZATION_TWITTER,
    'facebook': settings.ORGANIZATION_FACEBOOK,
    'address_name': settings.ORGANIZATION_ADDRESS_NAME,
    'address_1': settings.ORGANIZATION_ADDRESS_1,
    'address_2': settings.ORGANIZATION_ADDRESS_2,
    'address_phone': settings.ORGANIZATION_ADDRESS_PHONE
}

# serialize records
def programs_results(request, program_type, page):
    programs = None
    program_ct = 0
    # TODO: re-enable program type search or remove type filter
    qry = Program.objects.filter(available_for_sponsorship=True,
                                 program_type__program_type='RESIDENTIAL')
    # TODO: re-enable program search or remove
    # if program_type != 'Z':
    #    qry = qry.filter(program_type=program_type)
    program_ct = qry.count()
    if program_ct == 0:
        program_data = {'programsearch': {
            'count': 0, 'last_page': True, 'programs': []}}
        data = json.dumps(program_data)
        return HttpResponse(data, content_type='application/json')
    qry = qry.prefetch_related('program_type', 'family_set', 'child_set')
    pag = Paginator(qry, 15, orphans=3)
    try:
        programs = pag.page(page)
    except PageNotAnInteger:
        programs = pag.page(1)
    except EmptyPage:
        # page number out of range; return nothing
        program_data = {'programsearch': {'count': program_ct, 'last_page': True,
                                          'programs': []}}
        data = json.dumps(program_data)
        return HttpResponse(data, content_type='application/json')
    last_page = True
    if programs.has_next():
        last_page = False
    program_list = []
    for prog in programs:
        family_ct = prog.family_set.count()
        children = list(prog.child_set.all())
        aprog = {'id': prog.id, 'desc': prog.program_name, 'site': prog.program_site,
                 'family_count': family_ct, 'children_count': len(children)}
        gen_items = WishlistChild.objects.filter(
            child__in=children).prefetch_related(
            'category', 'item')
        items = gen_items.filter(have_other=False).values(
            'category__category', 'item__item_name').annotate(
            item_count=Count('item')).order_by()
        types_list = []
        for pt in prog.program_type.all():
            types_list.append(pt.__unicode__())
        if len(types_list) == 1:
            aprog['program_type'] = types_list[0]
        else:
            aprog['program_types'] = types_list
        wlist = []
        for itm in items:
            anitm = {'category': itm['category__category'], 'name': itm['item__item_name'],
                     'quantity': itm['item_count']}
            wlist.append(anitm)
        other_items = gen_items.filter(have_other=True).values(
            'category__category', 'other_item').annotate(
            other_item_count=Count('other_item')).order_by()
        for itm in other_items:
            anitm = {'category': itm['category__category'], 'name': itm['other_item'],
                     'quantity': itm['other_item_count']}
            wlist.append(anitm)
        aprog['wishlist'] = wlist
        program_list.append(aprog)
    program_data = {'programsearch': {'count': program_ct, 'last_page': last_page,
                                      'programs': program_list}}
    if programs:
        data = json.dumps(program_data)
    return HttpResponse(data, content_type='application/json')


def general_results(request, item_category, page):
    items = None
    qry = GeneralWishlistItem.objects.all()
    if item_category != 'Z':
        qry = qry.filter(category=item_category)
    print("found " + str(qry.count()) + " matches.")
    if qry.count() == 0:
        general_data = {'generalsearch': {'count': 0,
                                          'last_page': True, 'general_items': []}}
        data = json.dumps(general_data)
        return HttpResponse(data, content_type='application/json')
    general_ct = qry.count()
    pag = Paginator(qry, 20, orphans=5)  # 20 results per page; 5 minimum
    try:
        items = pag.page(page)
    except PageNotAnInteger:
        items = pag.page(1)
    except EmptyPage:
        # page number out of range; return nothing
        general_data = {'generalsearch': {'count': general_ct, 'last_page': True,
                                          'general_items': []}}
        data = json.dumps(general_data)
        return HttpResponse(data, content_type='application/json')
    last_page = True
    if items.has_next():
        last_page = False
    item_list = []
    for itm in items:
        anitem = {'id': itm.id, 'category': itm.category.__unicode__(),
                  'quantity': itm.quantity, 'notes': itm.notes}
        if itm.item:
            anitem['name'] = itm.item.__unicode__()
        else:
            anitem['name'] = itm.other_item
        item_list.append(anitem)
    general_data = {'generalsearch': {'count': general_ct, 'last_page': last_page,
                                      'general_items': item_list}}
    if items:
        data = json.dumps(general_data)
    return HttpResponse(data, content_type='application/json')


def families_results(request, program_type, family_size, urgent_need, page):
    families = None
    families_ct = 0
    # only count kids not already adopted/available for sponsorship
    # and only show families with at least one available kid
    qry = Family.objects.filter(available_for_sponsorship=True).filter(
        child__available_for_sponsorship=True).annotate(
        kid_count=Count('child')).filter(kid_count__gt=0)
    if program_type != 'Z':
        qry = qry.filter(program__program_type=program_type)
    if family_size != 'Z':
        if family_size == '2':
            # 2 (or less)
            qry = qry.filter(kid_count__lte=2)
        elif family_size == '3':
            qry = qry.filter(kid_count=3)
        elif family_size == '4':
            qry = qry.filter(kid_count=4)
        elif family_size == '5':
            # 5 or more kids
            qry = qry.filter(kid_count__gte=5)
    if urgent_need != 'Z':
        if urgent_need == 'T':
            qry = qry.filter(urgent_need=True)
        elif urgent_need == 'F':
            qry = qry.filter(urgent_need=False)
    families_ct = qry.count()
    if families_ct == 0:
        families_data = {'familysearch': {
            'count': 0, 'last_page': True, 'families': []}}
        data = json.dumps(families_data)
        return HttpResponse(data, content_type='application/json')
    qry = qry.select_related('program').prefetch_related(
        'child_set', 'child_set__clothing_size',
        'child_set__clothing_size__size_category', 'child_set__wishlistchild_set',
        'child_set__wishlistchild_set__category',
        'child_set__wishlistchild_set__item')
    # create paginator and get results for page
    # orphans in min # to have on last page
    pag = Paginator(qry, 20, orphans=5)  # 20 results per page; 5 minimum
    try:
        families = pag.page(page)
    except PageNotAnInteger:
        families = pag.page(1)
    except EmptyPage:
        # page number out of range; return nothing
        families_data = {'familysearch': {
            'count': families_ct, 'last_page': True, 'families': []}}
        data = json.dumps(families_data)
        return HttpResponse(data, content_type='application/json')
    last_page = True
    if families.has_next():
        last_page = False
    fam_list = []
    for fam in families:
        # only show kids not already adopted/available for sponsorship
        kids = [k for k in fam.child_set.all(
        ) if k.available_for_sponsorship is True]
        afam = {'id': fam.id,
                'desc': fam.__unicode__(),
                'urgent_need': fam.urgent_need,
                'program': fam.program.program_name,
                'program_site': fam.program.program_site,
                'family_size': len(kids)}
        kid_list = []
        for kid in kids:
            akid = {'desc': kid.__unicode__(
            ), 'clothing_size':  kid.clothing_size.__unicode__()}
            wishlist = kid.wishlistchild_set.all()
            wlist = []
            for wish in wishlist:
                awish = {'wish': wish.__unicode__()}
                if wish.notes:
                    awish['notes'] = wish.notes
                else:
                    awish['notes'] = ''
                wlist.append(awish)
            akid['wishlist'] = wlist
            kid_list.append(akid)
        afam['kids'] = kid_list
        fam_list.append(afam)
    families_data = {'familysearch': {'count': families_ct, 'last_page': last_page,
                                      'families': fam_list}}
    if families:
        data = json.dumps(families_data)
    return HttpResponse(data, content_type='application/json')


def children_results(request, gender, program_type, age_range, urgent_need, page):
    kids = None
    kid_ct = 0
    qry = Child.objects.filter(available_for_sponsorship=True)
    if gender != 'Z':
        qry = qry.filter(gender=gender)
    if program_type != 'Z':
        qry = qry.filter(program__program_type=program_type)
    if age_range != 'Z':
        if age_range == '0':
            # 0 to 4 years old
            qry = qry.filter(age__range=(0, 4))
        elif age_range == '1':
            # 5 to 9 years old
            qry = qry.filter(age__range=(5, 9))
        elif age_range == '2':
            # 10 to 14 years old
            qry = qry.filter(age__range=(10, 14))
        elif age_range == '3':
            # 15 to 19 years old
            qry = qry.filter(age__range=(15, 19))
        elif age_range == '4':
            # 20 to 25 years old
            qry = qry.filter(age__gte=20)  # >= 20
    if urgent_need != 'Z':
        if urgent_need == 'T':
            qry = qry.filter(urgent_need=True)
        else:
            qry = qry.filter(urgent_need=False)
    kid_ct = qry.count()
    if kid_ct == 0:
        kid_data = {'kidsearch': {'count': 0, 'last_page': True, 'kids': []}}
        data = json.dumps(kid_data)
        return HttpResponse(data, content_type='application/json')
    # create paginator and get results for page
    # orphans in min # to have on last page
    qry = qry.select_related('program').select_related(
        'clothing_size', 'clothing_size__size_category').prefetch_related(
        'wishlistchild_set', 'wishlistchild_set__category',
        'wishlistchild_set__item')
    pag = Paginator(qry, 20, orphans=5)  # 20 results per page; 5 minimum
    try:
        kids = pag.page(page)
    except PageNotAnInteger:
        kids = pag.page(1)
    except EmptyPage:
        # page number out of range; return nothing
        # kids = pag.page(pag.num_pages) # last page
        kid_data = {'kidsearch': {
            'count': kid_ct, 'last_page': True, 'kids': []}}
        data = json.dumps(kid_data)
        return HttpResponse(data, content_type='application/json')
    last_page = True
    if kids.has_next():
        last_page = False
    kid_list = []

    for kid in kids:
        akid = {'id': kid.id,
                # do not display name to visitor site (kid.first_name)
                'name': kid.id,
                'desc': kid.search_description(),
                'program': kid.program.program_name,
                'program_site': kid.program.program_site,
                'clothing_size': kid.clothing_size.__unicode__(),
                'urgent_need': kid.urgent_need}
        if kid.family_id:
            akid['family'] = kid.family_id
        else:
            akid['family'] = ''

        wishlist = kid.wishlistchild_set.all()
        wlist = []
        for wish in wishlist:
            awish = {'wish': wish.__unicode__()}
            if wish.notes:
                awish['notes'] = wish.notes
            else:
                awish['notes'] = ''
            wlist.append(awish)
        akid['wishlist'] = wlist
        kid_list.append(akid)
    kid_data = {'kidsearch': {'count': kid_ct,
                              'last_page': last_page, 'kids': kid_list}}
    if kids:
        data = json.dumps(kid_data)
    return HttpResponse(data, content_type='application/json')
###########################


# html email test view
# def test_email(request):
#    context_info = email_thanks(1, 1, 'child')
#    return render(request, 'email.html', context_info)

# email helper function #
def email_thanks(donor_id, thing_id, thing_type, request):
    donor = Donor.objects.get(id=donor_id)
    donor_name = donor.first_name
    donor_email = donor.email_address
    # thing_type may be child, family, program, or general
    if thing_type == 'child':
        child = Child.objects.get(id=thing_id)
        child_desc = child.search_description()
        size = child.clothing_size.__unicode__()
        item_information = [child_desc, 'Clothing size: ' + size,
                            'Program: ' + child.program.program_name]
        wishlist = WishlistChild.objects.filter(child=child)
        thing_desc = child.search_description()
        donation_label = child.program.program_name + ":  " + child.search_description()
    elif thing_type == 'family':
        fam = Family.objects.get(id=thing_id)
        thing_desc = fam.__unicode__()
        wishlist = WishlistChild.objects.filter(child__in=Child.objects.filter(
            family=fam).filter(available_for_sponsorship=True)).order_by('child')
        donation_label = fam.program.program_name + \
            " - Family " + str(fam.id)
        item_information = ['Program: ' + fam.program.program_name,
                            'Number of children: ' + str(Child.objects.filter(family=fam).filter(
                                available_for_sponsorship=True).count())]
    elif thing_type == 'program':
        program = Program.objects.get(id=thing_id)
        thing_desc = program.program_name
        donation_label = program.program_name
        families = Family.objects.filter(program=program).values('id')
        children = Child.objects.filter(program=program).values('id')
        item_information = ['Families in program: ' + str(families.count()),
                            'Children in program: ' + str(children.count())]
        # get wishlist with summary count and notes list
        items = WishlistChild.objects.filter(
            child__in=children).filter(have_other=False).values(
            'category__category', 'item__item_name').annotate(
            item_count=Count('item')).order_by()
        wishlist_items = items
        other_items = WishlistChild.objects.filter(
            child__in=children).filter(have_other=True).values(
            'category__category', 'other_item').annotate(
            other_item_count=Count('other_item')).order_by()
        wishlist_other_items = other_items
        wishlist = WishlistChild.objects.filter(
            child__in=children).order_by('child')
    elif thing_type == 'general':
        general = DonorGeneralWishlist.objects.get(id=thing_id)
        item = general.wishlist_item
        qty = general.quantity
        notes = item.notes
        wishlist = []  # no wishlist here
        if item.item:
            donation_label = item.item.item_name
        else:
            donation_label = item.other_item
        thing_desc = donation_label
        item_information = ['Item category: ' + item.category.category,
                            'Item: ' + donation_label]
        if notes:
            item_information.append(notes)
        item_information.append('Quantity pledged: ' + str(qty))
    else:
        # shouldn't happen
        print('unrecognized donation type in email_thanks!')
        return
    context_info = ORGANIZATION_CONTEXT.copy()
    if thing_type != 'program':
        context_info.update({'donor': donor_name, 'item_description': thing_desc,
                             'item_information': item_information, 'wishlist': wishlist,
                             'item_label': donation_label,
                             'domain': request.build_absolute_uri('/'),
        })
        text_content = render_to_string("email.txt", context_info)
        html_content = render_to_string("email.html", context_info)
    else:
        context_info.update({'donor': donor_name, 'item_description': thing_desc,
                             'item_information': item_information, 'wishlist_items': wishlist_items,
                             'wishlist_other_items': wishlist_other_items,
                             'item_label': donation_label, 'wishlist': wishlist})
        text_content = render_to_string("program_email.txt", context_info)
        html_content = render_to_string("program_email.html", context_info)

    # send email
    msg = EmailMultiAlternatives(settings.SITE_NAME,
                                 text_content, settings.ORGANIZATION_EMAIL, [donor_email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()

    if thing_type == 'family':
        # mark children no longer available for sponsorship
        Child.objects.filter(family=fam).filter(
            keep_available=False).update(available_for_sponsorship=False)
    ############


# VISITOR VIEWS
@never_cache
def thanks(request):
    return render(request, 'thanks.html', ORGANIZATION_CONTEXT)


def holiday_drive(request):
    # visitor main page
    if request.session.get('donor'):
        try:
            donor = Donor.objects.get(id=request.session.get('donor'))
            messages.success(request, "Thanks, " + donor.first_name +
                             "!  If you select to make another sponsorship now, you " +
                             "won't have to enter your contact information again.")
        except:
            pass  # shouldn't happen
    return render(request, 'holiday_drive.html', ORGANIZATION_CONTEXT)


@never_cache
def sponsor_program(request, program_id=None):
    # log IP address
    x_fwd = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = x_fwd.split(',')[0] if x_fwd else request.META.get('REMOTE_ADDR')

    if request.method == 'POST':
        form = SponsorInformation(request.POST)
        if form.is_valid():
            try:
                program = form.cleaned_data.get('adopted_programs')[0]
                program.available_for_sponsorship = False  # adopted already
                program.save()
                donor = form.save()
                # set IP adddress
                donor.entered_from_address = ip
                donor.save()
                messages.success(request, "saved successfully")
                # clear session so can't use back button and re-submit
                request.session.flush()
                request.session.clear_expired()
                request.session.set_expiry(0)  # clear on browser close
                # put donor ID in session data
                request.session['donor'] = donor.id
                # email
                try:
                    email_thanks(donor.id, program.id, 'program', request)
                except:
                    storage = messages.get_messages(request)
                    storage.used = True  # clear success message, if any
                    messages.error(
                        request, "We're sorry, but the email failed to send.")
                context = ORGANIZATION_CONTEXT.copy()
                context.update({'donation_label': program.program_name})
                return render(request, 'thanks.html', context)
            except:
                storage = messages.get_messages(request)
                storage.used = True  # clear success message, if any
                messages.error(
                    request, "We're sorry, but the form failed to submit")
        else:
            # invalid form; get program for label
            program = Program.objects.get(id=request.POST['adopted_programs'])
    else:
        # check that this is a valid program id for sponsorship
        if not program_id:
            messages.error(
                request, "No matching program found to sponsor.  Please search again.")
            return redirect(search_programs)
        program = Program.objects.filter(id=program_id)
        if not program.exists():
            # invalid program_id kwarg; shouldn't happen
            messages.error(
                request, "No matching program found to sponsor.  Please search again.")
            return redirect(search_programs)
        elif not program[0].available_for_sponsorship:
            # should only happen if child sponsored after visitor did search
            messages.error(request, "We're sorry, but " + program[0].program_name +
                           " is no longer available for sponsorship.  Please search again.")
            return redirect(search_programs)
        else:
            program = program[0]
        # ID is valid.  Is this sponsor making an additional sponsorship?
        if request.session.get('donor'):
            try:
                donor = Donor.objects.get(id=request.session.get('donor'))
                # got returning sponsor; update and thank
                donor.adopted_programs.add(program)
                donor.save()
                program.available_for_sponsorship = False
                program.save()
                messages.success(request, "Sponsorship of " + program.program_name +
                                 " saved successfully.  Thanks " + donor.first_name + "!")
                # email
                try:
                    email_thanks(donor.id, program.id, 'program', request)
                except:
                    storage = messages.get_messages(request)
                    storage.used = True  # clear success message, if any
                    messages.error(
                        request, "We're sorry, but the email failed to send.")
                context = ORGANIZATION_CONTEXT.copy()
                context.update({'donation_label': program.program_name})
                return render(request, 'thanks.html', context)
            except:
                storage = messages.get_messages(request)
                storage.used = True  # clear success message, if any
                messages.error(request, "We're sorry, but your sponsorship of " +
                               program.program_name + " was not saved successfully.")
        form = SponsorInformation(initial={'adopted_programs': [program_id, ]})
    context = ORGANIZATION_CONTEXT.copy()
    context.update({'form': form, 'title': program.program_name})
    return render(request, 'visitor_sponsor_form.html', context)


@never_cache
def sponsor_general(request, item_id=None, qty=1):
    # log IP address
    x_fwd = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = x_fwd.split(',')[0] if x_fwd else request.META.get('REMOTE_ADDR')
    context = ORGANIZATION_CONTEXT.copy()
    item_name = ''
    if request.method == 'POST':
        form = SponsorInformation(request.POST, prefix='donor')
        item_form = DonorItemsForm(request.POST, prefix='item')
        if not item_form.is_valid():
            # do anything?
            print("item form invalid")
        if form.is_valid():
            try:
                item = item_form.cleaned_data.get('items')[0]
                donor = form.save()
                donor_wishlist = DonorGeneralWishlist()
                donor.entered_from_address = ip
                donor_wishlist.donor = donor
                donor_wishlist.wishlist_item = item
                donor_wishlist.quantity = item_form.cleaned_data.get(
                    'quantity')
                donor_wishlist.save()
                item.quantity_pledged += item_form.cleaned_data.get('quantity')
                item.save()
                messages.success(request, "saved successfully")
                # clear session so can't use back button and re-submit
                request.session.flush()
                request.session.clear_expired()
                request.session.set_expiry(0)  # clear on browser close
                # ...then put donor ID in session data
                request.session['donor'] = donor.id
                if item.item:
                    item_name = item.item.item_name
                else:
                    item_name = item.other_item
                # email
                try:
                    email_thanks(donor.id, donor_wishlist.id, 'general', request)
                except:
                    storage = messages.get_messages(request)
                    storage.used = True  # clear success message, if any
                    messages.error(
                        request, "We're sorry, but the email failed to send.")
                context.update({'donation_label': item_name})
                return render(request, 'thanks.html', context)
            except:
                storage = messages.get_messages(request)
                storage.used = True  # clear success message, if any
                messages.error(request, "We're sorry, but the form " +
                               "failed to submit properly.")
        else:
            # invalid form; get item for label
            item = GeneralWishlistItem.objects.get(
                id=request.POST['item-items'])
            if item.item:
                item_name = item.item.item_name
            else:
                item_name = item.other_item
    else:
        # check that this is a valid item id for sponsorship
        try:
            item = GeneralWishlistItem.objects.filter(id=item_id)
        except:
            messages.error(request, "No matching item found to sponsor.")
            return redirect(search_general)  # redirect to wishlist search
        if not item.exists():
            # invalid child_id kwarg; shouldn't happen
            messages.error(request, "No matching item found to sponsor.")
            return redirect(search_general)  # redirect to wishlist search
        else:
            item = item[0]
        if item.item:
            item_name = item.item.item_name
        else:
            item_name = item.other_item
        if not qty or not qty.isdigit():
            # invalid quantity (shouldn't happen)
            messages.error(request, "Invalid quantity for item.")
            return redirect(search_general)  # redirect to wishlist search
        # ID is valid.  Is this sponsor making an additional sponsorship?
        if request.session.get('donor'):
            print("got returning donor")
            try:
                # got returning sponsor; update and thank
                donor = Donor.objects.get(id=request.session.get('donor'))
                donor_wishlist = DonorGeneralWishlist()
                donor_wishlist.donor = donor
                donor_wishlist.wishlist_item = item
                donor_wishlist.quantity = int(qty)
                donor_wishlist.save()
                item.quantity_pledged += int(qty)
                item.save()
                messages.success(request, "Sponsorship of " + qty + " of " + item_name +
                                 " saved successfully.  Thanks " + donor.first_name + "!")
                # email
                try:
                    email_thanks(donor.id, donor_wishlist.id, 'general', request)
                except:
                    storage = messages.get_messages(request)
                    storage.used = True  # clear success message, if any
                    messages.error(
                        request, "We're sorry, but the email failed to send.")
                context.update({'donation_label': item_name})
                return render(request, 'thanks.html', context)
            except:
                storage = messages.get_messages(request)
                storage.used = True  # clear success message, if any
                messages.error(request, "We're sorry, but your sponsorship of " +
                               qty + " of " + item_name + " was not saved successfully.")
        form = SponsorInformation(prefix='donor')
        item_form = DonorItemsForm(initial={'items': [item_id, ],
                                            'quantity': qty}, prefix='item')
    context.update({'form': form, 'title': 'item ' + item_name, 'item_form': item_form})
    return render(request, 'visitor_sponsor_form.html', context)


@never_cache
def sponsor_family(request, family_id=None):
    # log IP address
    x_fwd = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = x_fwd.split(',')[0] if x_fwd else request.META.get('REMOTE_ADDR')
    context = ORGANIZATION_CONTEXT.copy()
    if request.method == 'POST':
        form = SponsorInformation(request.POST)
        if form.is_valid():
            try:
                family = form.cleaned_data.get('adopted_families')[0]
                if not family.keep_available:
                    family.available_for_sponsorship = False
                    # mark kids once email sent
                    # Child.objects.filter(family=family).filter(
                    #  keep_available=False).update(available_for_sponsorship=False)
                    family.save()
                donor = form.save()
                # set IP adddress
                donor.entered_from_address = ip
                donor.save()
                messages.success(request, "saved successfully")
                # clear session so can't use back button and re-submit
                request.session.flush()
                request.session.clear_expired()
                request.session.set_expiry(0)  # clear on browser close
                # put donor ID in session data
                request.session['donor'] = donor.id
                # email
                try:
                    email_thanks(donor.id, family.id, 'family', request)
                except:
                    storage = messages.get_messages(request)
                    storage.used = True  # clear success message, if any
                    messages.error(
                        request, "We're sorry, but the email failed to send.")
                context.update({'donation_label': family.program.program_name +
                                " - Family " + str(family.id)})
                return render(request, 'thanks.html', context)
            except:
                storage = messages.get_messages(request)
                storage.used = True  # clear success message, if any
                messages.error(
                    request, "We're sorry, but the form failed to submit")
        else:
            # invalid form; get family for label
            family = Family.objects.get(id=request.POST['adopted_families'])
    else:
        # check that this is a valid family id for sponsorship
        family = Family.objects.filter(id=family_id)
        if not family.exists():
            # invalid family_id kwarg; shouldn't happen
            messages.error(request, "No matching family found to sponsor.")
            return redirect(search_families)
        elif not family[0].available_for_sponsorship:
            # should only happen if family sponsored/made unavailable
            # after visitor did search
            messages.error(request, "We're sorry, but family " + str(family[0].id) +
                           " is no longer available for sponsorship.")
            return redirect(search_families)
        else:
            family = family[0]
        # ID is valid.  Is this sponsor making an additional sponsorship?
        if request.session.get('donor'):
            try:
                # got returning sponsor; update and thank
                donor = Donor.objects.get(id=request.session.get('donor'))
                donor.adopted_families.add(family)
                donor.save()
                if not family.keep_available:
                    family.available_for_sponsorship = False
                    # mark kids once email sent
                    # Child.objects.filter(family=family).filter(
                    #  keep_available=False).update(available_for_sponsorship=False)
                    family.save()
                messages.success(request, "Sponsorship of " + family.__unicode__() +
                                 " saved successfully.  Thanks " + donor.first_name + "!")
                # email
                try:
                    email_thanks(donor.id, family.id, 'family', request)
                except:
                    storage = messages.get_messages(request)
                    storage.used = True  # clear success message, if any
                    messages.error(
                        request, "We're sorry, but the email failed to send.")
                context.update({'donation_label': family.program.program_name + " - Family " + str(family.id)})
                return render(request, 'thanks.html', context)
            except:
                storage = messages.get_messages(request)
                storage.used = True  # clear success message, if any
                messages.error(request, "We're sorry, but your sponsorship of " +
                               family.__unicode__() + " was not saved successfully.")
        form = SponsorInformation(initial={'adopted_families': [family_id, ]})
    context.update({'form': form, 'title': 'family ' + str(family.id)})
    return render(request, 'visitor_sponsor_form.html', context)


@never_cache
def sponsor_child(request, child_id=None):
    # log IP address
    x_fwd = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = x_fwd.split(',')[0] if x_fwd else request.META.get('REMOTE_ADDR')
    context = ORGANIZATION_CONTEXT.copy()
    if request.method == 'POST':
        form = SponsorInformation(request.POST)
        if form.is_valid():
            try:
                child = form.cleaned_data.get('adopted_children')[0]
                if not child.keep_available:
                    child.available_for_sponsorship = False
                    child.save()
                # can get child's donor(s) later with child.donor_set.all()
                # child.donor_set.count() etc.
                donor = form.save()
                # set IP adddress
                donor.entered_from_address = ip
                donor.save()
                messages.success(request, "saved successfully")
                # clear session so can't use back button and re-submit
                request.session.flush()
                request.session.clear_expired()
                request.session.set_expiry(0)  # clear on browser close
                # put donor ID in session data
                request.session['donor'] = donor.id
                # email
                try:
                    email_thanks(donor.id, child.id, 'child', request)
                except:
                    storage = messages.get_messages(request)
                    storage.used = True  # clear success message, if any
                    messages.error(
                        request, "We're sorry, but the email failed to send.")
                context.update({'donation_label': child.program.program_name + ":  " + child.search_description()})
                return render(request, 'thanks.html', context)
            except:
                storage = messages.get_messages(request)
                storage.used = True  # clear success message, if any
                messages.error(
                    request, "We're sorry, but the form failed to submit.")
        else:
            # invalid form; get child for label
            child = Child.objects.get(id=request.POST['adopted_children'])
    else:
        # check that this is a valid child id for sponsorship
        if not child_id:
            messages.error(
                request, "No matching child found to sponsor.  Please search again.")
            return redirect(search_children)
        child = Child.objects.filter(id=child_id)
        if not child.exists():
            # invalid child_id kwarg; shouldn't happen
            messages.error(
                request, "No matching child found to sponsor.  Please search again.")
            return redirect(search_children)
        elif not child[0].available_for_sponsorship:
            # should only happen if child sponsored after visitor did search
            # messages.error(request, "We're sorry, but " + child[0].first_name +
            #  " is no longer available for sponsorship.  Please search again.")
            messages.error(request, "We're sorry, but the selected child " +
                           " is no longer available for sponsorship.  Please search again.")
            return redirect(search_children)
        else:
            child = child[0]
        # ID is valid.  Is this sponsor making an additional sponsorship?
        if request.session.get('donor'):
            try:
                donor = Donor.objects.get(id=request.session.get('donor'))
                # got returning sponsor; update and thank
                donor.adopted_children.add(child)
                donor.save()
                if not child.keep_available:
                    child.available_for_sponsorship = False
                    child.save()
                messages.success(request, "Sponsorship of " + child.search_description() +
                                 " saved successfully.  Thanks " + donor.first_name + "!")
                # email
                try:
                    email_thanks(donor.id, child.id, 'child', request)
                except:
                    storage = messages.get_messages(request)
                    storage.used = True  # clear success message, if any
                    messages.error(request,
                                   "We're sorry, but the email was not sent successfully.")
                context.update({'donation_label': child.program.program_name +
                                 ":  " + child.search_description()})
                return render(request, 'thanks.html', context)
            except:
                storage = messages.get_messages(request)
                storage.used = True  # clear success message, if any
                messages.error(request, "We're sorry, but your sponsorship of " +
                               "the child was not saved successfully.")
        form = SponsorInformation(initial={'adopted_children': [child_id, ]})
        context.update({'form': form, 'title': child.search_description()})
    return render(request, 'visitor_sponsor_form.html', context)


def search_children(request):
    context = ORGANIZATION_CONTEXT.copy()
    gender = program_type = age_group = urgent_need = 'Z'
    if request.method == 'POST':
        form = SearchChildren(request.POST)
        if form.is_valid():
            if 'gender' in request.POST and len(request.POST['gender']) > 0:
                gender = request.POST['gender']
            if ('program_type' in request.POST and len(request.POST['program_type']) > 0):
                program_type = request.POST['program_type']
            if 'age_range' in request.POST and len(request.POST['age_range']) > 0:
                age_group = request.POST['age_range']
            if ('urgent_need' in request.POST and len(request.POST['urgent_need']) > 0):
                urgent_need = request.POST['urgent_need']
    else:
        form = SearchChildren()
    json_url = '/fetch/searchkids/' + gender + '/' + str(program_type) + \
        '/' + str(age_group) + '/' + str(urgent_need) + '/'
    context.update({'form': form, 'json_url': json_url})
    return render(request, 'children_search.html', context)


def search_families(request):
    context = ORGANIZATION_CONTEXT.copy()
    program_type = family_size = urgent_need = 'Z'
    if request.method == 'POST':
        form = SearchFamilies(request.POST)
        if form.is_valid():
            if 'program_type' in request.POST and len(request.POST['program_type']) > 0:
                program_type = request.POST['program_type']
            if 'family_size' in request.POST and len(request.POST['family_size']) > 0:
                family_size = request.POST['family_size']
            if 'urgent_need' in request.POST and len(request.POST['urgent_need']) > 0:
                urgent_need = request.POST['urgent_need']
    else:
        form = SearchFamilies()
    json_url = '/fetch/searchfamilies/' + str(program_type) + \
        '/' + str(family_size) + '/' + str(urgent_need) + '/'
    context.update({'form': form, 'json_url': json_url})
    return render(request, 'families_search.html', context)


def search_general(request):
    context = ORGANIZATION_CONTEXT.copy()
    item_category = 'Z'
    if request.method == 'POST':
        form = SearchGeneral(request.POST)
        if form.is_valid():
            if 'item_category' in request.POST and len(request.POST['item_category']) > 0:
                item_category = request.POST['item_category']
    else:
        form = SearchGeneral()
    json_url = '/fetch/searchgeneral/' + str(item_category) + '/'
    context.update({'form': form, 'json_url': json_url})
    return render(request, 'general_search.html', context)


def search_programs(request):
    # TODO: re-enable search or remove search
    # program_type = 'Z'
    # if request.method == 'POST':
    #     form = SearchPrograms(request.POST)
    #     if form.is_valid():
    #         if 'program_type' in request.POST and len(request.POST['program_type']) > 0:
    #                 program_type = request.POST['program_type']
    # else:
    #     form = SearchPrograms()
    form = SearchPrograms()
    program_type = 'Z'
    json_url = '/fetch/searchprograms/' + str(program_type) + '/'
    context = ORGANIZATION_CONTEXT.copy()
    context.update({'form': form, 'json_url': json_url})
    return render(request, 'program_search.html', context)
