document.addEventListener('DOMContentLoaded', function() {
    console.log('JavaScript loaded');
    // ফর্ম ভ্যালিডেশন বা অতিরিক্ত ফাংশনালিটি
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const inputs = form.querySelectorAll('input[required]');
            inputs.forEach(input => {
                if (!input.value) {
                    e.preventDefault();
                    input.classList.add('is-invalid');
                } else {
                    input.classList.remove('is-invalid');
                }
            });
        });
    });
});
