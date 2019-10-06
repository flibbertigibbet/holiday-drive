from holiday.models import *
from django.contrib.auth.admin import UserAdmin
from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models import NullBooleanField
from django.forms.widgets import CheckboxInput
from django.forms import ModelForm, ValidationError
from django_admin_bootstrapped.admin.models import SortableInline

# Define an inline admin descriptor for Member model
# which acts a bit like a singleton


class ProgramStaffInline(admin.StackedInline):
    model = ProgramStaff
    can_delete = False
    verbose_name_plural = 'program staff'

    formfield_overrides = {
        NullBooleanField: {'widget': CheckboxInput},
    }

# Define a new User admin


class UserAdmin(UserAdmin):
    inlines = (ProgramStaffInline, )


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


class FamilyAdminForm(ModelForm):
    class Meta:
        model = Family
        fields = '__all__'

    def clean(self):
        clean_data = super(FamilyAdminForm, self).clean()
        keep_unavailable = clean_data.get('keep_unavailable')
        keep_available = clean_data.get('keep_available')
        if keep_unavailable and keep_available:
            raise ValidationError(u'Cannot keep family both available and unavailable ' +
                                  'for sponsorship.  Please select one or the other.')


class FamilyAdmin(admin.ModelAdmin):
    form = FamilyAdminForm
    actions = ['keep_available', 'keep_unavailable', 'urgent_need']

    def urgent_need(self, request, queryset):
        try:
            rows_updated = queryset.update(urgent_need=True)
            if rows_updated == 1:
                message_str = "One family and its"
            else:
                message_str = "%s families and their" % rows_updated
            # mark kids in family, too
            kids_updated = Child.objects.filter(
                family__in=queryset).update(urgent_need=True)
            if kids_updated == 1:
                message_str += " one child successfully marked as being in urgent need."
            else:
                message_str += " %s children successfully marked as being in urgent need." % kids_updated

            self.message_user(request, message_str)
        except:
            self.message_user(request, "Oops!  Action failed.")

    def keep_available(self, request, queryset):
        try:
            rows_updated = queryset.update(keep_available=True, keep_unavailable=False,
                                           available_for_sponsorship=True)
            if rows_updated == 1:
                message_str = "One family and its"
            else:
                message_str = "%s families and their" % rows_updated
            # mark kids in family, too
            kids_updated = Child.objects.filter(family__in=queryset).update(keep_available=True,
                                                                            keep_unavailable=False, available_for_sponsorship=True)
            if kids_updated == 1:
                message_str += " one child successfully marked to keep available."
            else:
                message_str += " %s children successfully marked to keep available." % kids_updated

            self.message_user(request, message_str)
        except:
            self.message_user(request, "Oops!  Action failed.")

    def keep_unavailable(self, request, queryset):
        try:
            rows_updated = queryset.update(keep_available=False, keep_unavailable=True,
                                           available_for_sponsorship=False)
            if rows_updated == 1:
                message_str = "One family and its"
            else:
                message_str = "%s families and their" % rows_updated
            # mark kids in family, too
            kids_updated = Child.objects.filter(family__in=queryset).update(keep_available=False,
                                                                            keep_unavailable=True, available_for_sponsorship=False)
            if kids_updated == 1:
                message_str += " one child successfully marked to keep unavailable."
            else:
                message_str += " %s children successfully marked to keep unavailable." % kids_updated

            self.message_user(request, message_str)
        except:
            self.message_user(request, "Oops!  Action failed.")

    keep_available.short_description = "Keep selected families available"
    keep_unavailable.short_description = "Keep selected families unavailable"
    urgent_need.short_description = "Mark selected families as being in urgent need"

    def save_model(self, request, obj, form, change):
        obj.staff_entering = request.user  # staff_entering is last person to touch record
        # also update kids in family to keep (un-)available
        kids = Child.objects.filter(family=obj)
        if obj.keep_unavailable:
            obj.available_for_sponsorship = False
            kids.update(keep_unavailable=True, keep_available=False,
                        available_for_sponsorship=False)
        elif obj.keep_available:
            obj.available_for_sponsorship = True
            kids.update(keep_unavailable=False, keep_available=True,
                        available_for_sponsorship=True)
        elif obj.approved:
            obj.available_for_sponsorship = True
        else:
            # not approved by program director
            obj.available_for_sponsorship = False

        obj.save()


class ChildAdminForm(ModelForm):
    class Meta:
        model = Child
        fields = '__all__'

    def clean(self):
        clean_data = super(ChildAdminForm, self).clean()
        keep_unavailable = clean_data.get('keep_unavailable')
        keep_available = clean_data.get('keep_available')
        if keep_unavailable and keep_available:
            raise ValidationError(u'Cannot keep child both available and unavailable ' +
                                  'for sponsorship.  Please select one or the other.')


class WishlistChildInline(admin.StackedInline, SortableInline):
    model = WishlistChild
    extra = 0


class ChildAdmin(admin.ModelAdmin):
    form = ChildAdminForm
    actions = ['keep_available', 'keep_unavailable', 'urgent_need']
    inlines = [WishlistChildInline]
    list_filter = ('approved', 'available_for_sponsorship', 'program')

    def save_model(self, request, obj, form, change):
        obj.staff_entering = request.user  # staff_entering is last person to touch record
        if obj.keep_unavailable:
            obj.available_for_sponsorship = False
        elif obj.keep_available:
            obj.available_for_sponsorship = True
        elif obj.approved:
            obj.available_for_sponsorship = True
        else:
            # not approved by program director
            obj.available_for_sponsorship = False

        obj.save()

    def urgent_need(self, request, queryset):
        try:
            rows_updated = queryset.update(urgent_need=True)
            if rows_updated == 1:
                message_str = "One child successfully marked as being in urgent need."
            else:
                message_str = "%s children successfully marked as being in urgent need." % rows_updated

            self.message_user(request, message_str)
        except:
            self.message_user(request, "Oops!  Action failed.")

    def keep_available(self, request, queryset):
        try:
            rows_updated = queryset.update(keep_available=True, keep_unavailable=False,
                                           available_for_sponsorship=True)
            if rows_updated == 1:
                message_str = "One child successfully marked to keep available."
            else:
                message_str = "%s children successfully marked to keep available." % rows_updated

            self.message_user(request, message_str)
        except:
            self.message_user(request, "Oops!  Action failed.")

    def keep_unavailable(self, request, queryset):
        try:
            rows_updated = queryset.update(keep_available=False, keep_unavailable=True,
                                           available_for_sponsorship=False)
            if rows_updated == 1:
                message_str = "One child successfully marked to keep unavailable."
            else:
                message_str = "%s children successfully marked to keep unavailable." % rows_updated

            self.message_user(request, message_str)
        except:
            self.message_user(request, "Oops!  Action failed.")

    keep_available.short_description = "Keep selected children available"
    keep_unavailable.short_description = "Keep selected children unavailable"
    urgent_need.short_description = "Mark selected children as being in urgent need"


class GeneralWishlistItemForm(ModelForm):
    class Meta:
        model = GeneralWishlistItem
        fields = '__all__'

    def clean(self):
        clean_data = super(GeneralWishlistItemForm, self).clean()
        have_other = clean_data.get('have_other')
        other_item = clean_data.get('other_item')
        item = clean_data.get('item')

        if not item and not have_other:
            self._errors['item'] = self.error_class([
                u'Please select an item from the list, or enter something for "other item."'])
        elif have_other and not other_item:
            self._errors['other_item'] = self.error_class([
                u'Please enter a description for the item here.'])


class WishlistItemInline(admin.StackedInline, SortableInline):
    model = WishlistItem
    extra = 0


class WishlistItemCategoryAdmin(admin.ModelAdmin):
    inlines = [WishlistItemInline, ]


class GeneralWishlistAdmin(admin.ModelAdmin):
    form = GeneralWishlistItemForm
    change_form_template = 'admin/generalwishlist_form.html'
    add_form_template = 'admin/generalwishlist_form.html'
    formfield_overrides = {'have_other': CheckboxInput}


class ClothingSizeCategoryInline(admin.StackedInline, SortableInline):
    model = ClothingSizeCategory
    extra = 0


class ClothingSizeInline(admin.StackedInline, SortableInline):
    model = ClothingSize
    extra = 0


class ClothingSizeCategoryAdmin(admin.ModelAdmin):
    inlines = [ClothingSizeInline, ]


class DonorGeneralInline(admin.StackedInline, SortableInline):
    model = DonorGeneralWishlist
    extra = 0


class DonorAdmin(admin.ModelAdmin):
    inlines = [DonorGeneralInline, ]


class ProgramAdmin(admin.ModelAdmin):
    actions = ['available_for_sponsorship']

    def available_for_sponsorship(self, request, queryset):
        try:
            rows_updated = queryset.update(available_for_sponsorship=True)
            if rows_updated == 1:
                message_str = "One program "
            else:
                message_str = "%s programs " % rows_updated

            message_str += "successfully marked as available for sponsorship"
            self.message_user(request, message_str)
        except:
            self.message_user(request, "Oops!  Action failed.")


admin.site.register(ClothingSizeCategory, ClothingSizeCategoryAdmin)
admin.site.register(ClothingSize)
admin.site.register(Family, FamilyAdmin)
admin.site.register(Child, ChildAdmin)
admin.site.register(GeneralWishlistItem, GeneralWishlistAdmin)
admin.site.register(ProgramType)
admin.site.register(Program, ProgramAdmin)
admin.site.register(WishlistItemCategory, WishlistItemCategoryAdmin)
admin.site.register(WishlistItem)
admin.site.register(Donor, DonorAdmin)
admin.site.register(DonorGeneralWishlist)
admin.site.register(State)
admin.site.register(DirectorMultiPrograms)
admin.site.register(ProgramMaximumChildren)
